"""
filesystem_service.py — Core virtual filesystem operations.
Implements path resolution, tree traversal, node CRUD, inode management,
hard-link and symbolic-link logic, and physical block allocation.
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models import FilesystemNode, DiskBlock
from datetime import datetime, timezone

BLOCK_SIZE = 512
TOTAL_BLOCKS = 256
DATA_START_BLOCK = 33 # Blocks 0-32 reserved (0=Superblock, 1-32=Inode table)


def _utcnow():
    return datetime.now(timezone.utc)


# ── Block Allocation & Free Space Management ─────────────────

def ensure_disk_blocks(db: Session):
    """Ensure that all 256 virtual disk blocks are created in the database."""
    if db.query(DiskBlock).count() == 0:
        for b in range(TOTAL_BLOCKS):
            db.add(DiskBlock(block_number=b, inode_number=None, block_index=None))
        db.commit()


def get_disk_usage(db: Session) -> dict:
    """Get total, used, and free disk blocks/space metrics."""
    ensure_disk_blocks(db)
    
    # Blocks 0 to 32 are reserved
    reserved_blocks = DATA_START_BLOCK
    
    # Used data blocks are those allocated to an inode
    used_data_blocks = db.query(DiskBlock).filter(
        DiskBlock.block_number >= DATA_START_BLOCK,
        DiskBlock.inode_number.isnot(None)
    ).count()
    
    used_total = reserved_blocks + used_data_blocks
    free_blocks = TOTAL_BLOCKS - used_total

    return {
        "total_blocks": TOTAL_BLOCKS,
        "used_blocks": used_total,
        "free_blocks": free_blocks,
        "block_size": BLOCK_SIZE,
        "total_space_bytes": TOTAL_BLOCKS * BLOCK_SIZE,
        "used_space_bytes": used_total * BLOCK_SIZE,
        "free_space_bytes": free_blocks * BLOCK_SIZE
    }


def allocate_blocks_for_inode(db: Session, inode_number: int, size_bytes: int):
    """
    Allocate or release blocks to match the file's current size.
    Raises IOError if there are not enough free blocks.
    """
    ensure_disk_blocks(db)
    blocks_needed = (size_bytes + BLOCK_SIZE - 1) // BLOCK_SIZE if size_bytes > 0 else 0

    # Query currently allocated blocks for this inode ordered by block_index
    current_blocks = db.query(DiskBlock).filter(
        DiskBlock.inode_number == inode_number
    ).order_by(DiskBlock.block_index).all()
    current_count = len(current_blocks)

    if blocks_needed == current_count:
        return

    if blocks_needed < current_count:
        # Release extra blocks
        for block in current_blocks[blocks_needed:]:
            block.inode_number = None
            block.block_index = None
        db.commit()
    else:
        # We need more blocks
        additional_needed = blocks_needed - current_count
        
        # Query free blocks (block_number >= 33 and inode_number is null)
        free_blocks = db.query(DiskBlock).filter(
            DiskBlock.block_number >= DATA_START_BLOCK,
            DiskBlock.inode_number.is_(None)
        ).order_by(DiskBlock.block_number).all()

        if len(free_blocks) < additional_needed:
            raise IOError("No space left on device: Disk is full")

        # Assign free blocks
        for i in range(additional_needed):
            block = free_blocks[i]
            block.inode_number = inode_number
            block.block_index = current_count + i
        db.commit()


def recalculate_directory_sizes(db: Session, parent_id: Optional[int]):
    """
    Recalculates size and block allocation of directory nodes up the tree.
    In Unix, a directory size is proportional to the number of entries.
    Each entry (. , .. , and children) is simulated as 32 bytes.
    """
    current_id = parent_id
    while current_id is not None:
        dir_node = db.query(FilesystemNode).get(current_id)
        if not dir_node or dir_node.node_type != "directory":
            break

        # Count direct children
        child_count = db.query(FilesystemNode).filter(
            FilesystemNode.parent_id == dir_node.id
        ).count()

        # Entries = child_count + 2 (for . and ..)
        entry_count = child_count + 2
        dir_node.size_bytes = entry_count * 32
        dir_node.modified_at = _utcnow()
        
        # Update block allocation
        allocate_blocks_for_inode(db, dir_node.inode_number, dir_node.size_bytes)
        
        current_id = dir_node.parent_id


# ── Path Resolution ───────────────────────────────────────────

def get_root(db: Session) -> FilesystemNode:
    """Return the root node (name='/')."""
    return db.query(FilesystemNode).filter(
        FilesystemNode.name == "/", FilesystemNode.parent_id.is_(None)
    ).first()


def resolve_path(db: Session, path: str, cwd_id: Optional[int] = None) -> Optional[FilesystemNode]:
    """
    Resolve an absolute or relative path string to a FilesystemNode.
    Supports '/', '..', '.', and nested paths.
    """
    if not path:
        return None

    # Determine starting node
    if path.startswith("/"):
        current = get_root(db)
        path = path.lstrip("/")
    else:
        current = db.query(FilesystemNode).get(cwd_id) if cwd_id else get_root(db)

    if not path:
        return current

    parts = [p for p in path.split("/") if p]

    for part in parts:
        if current is None:
            return None
        if part == ".":
            continue
        elif part == "..":
            if current.parent_id:
                current = db.query(FilesystemNode).get(current.parent_id)
            else:
                current = get_root(db)  # root's parent is root
        else:
            child = db.query(FilesystemNode).filter(
                FilesystemNode.parent_id == current.id,
                FilesystemNode.name == part,
            ).first()
            if child is None:
                return None
            # Follow symlinks
            if child.node_type == "symlink" and child.target_path:
                resolved = resolve_path(db, child.target_path)
                if resolved is None:
                    return None  # broken symlink
                current = resolved
            else:
                current = child

    return current


def get_node_path(db: Session, node: FilesystemNode) -> str:
    """Build the full path string for a node by traversing up to root."""
    parts = []
    current = node
    seen = set()
    while current:
        if current.id in seen:
            break
        seen.add(current.id)
        if current.name == "/":
            break
        parts.append(current.name)
        if current.parent_id:
            current = db.query(FilesystemNode).get(current.parent_id)
        else:
            break
    parts.reverse()
    return "/" + "/".join(parts)


# ── Tree Traversal ────────────────────────────────────────────

def build_tree(db: Session, node_id: Optional[int] = None) -> dict:
    """Build an in-memory tree dict from the root using DFS."""
    if node_id is None:
        root = get_root(db)
        if root is None:
            return {}
        node_id = root.id

    node = db.query(FilesystemNode).get(node_id)
    if node is None:
        return {}

    children_rows = db.query(FilesystemNode).filter(
        FilesystemNode.parent_id == node.id
    ).order_by(FilesystemNode.node_type.desc(), FilesystemNode.name).all()

    return {
        "id": node.id,
        "inode_number": node.inode_number,
        "name": node.name,
        "node_type": node.node_type,
        "size_bytes": node.size_bytes,
        "target_path": node.target_path,
        "children": [build_tree(db, c.id) for c in children_rows],
    }


def list_children(db: Session, parent_id: int) -> List[FilesystemNode]:
    """List all direct children of a directory."""
    return db.query(FilesystemNode).filter(
        FilesystemNode.parent_id == parent_id
    ).order_by(FilesystemNode.node_type.desc(), FilesystemNode.name).all()


# ── CRUD ──────────────────────────────────────────────────────

def get_node_by_id(db: Session, node_id: int) -> Optional[FilesystemNode]:
    return db.query(FilesystemNode).get(node_id)


def get_all_nodes(db: Session) -> List[FilesystemNode]:
    return db.query(FilesystemNode).all()


def get_next_inode(db: Session) -> int:
    from sqlalchemy import func
    max_inode = db.query(func.max(FilesystemNode.inode_number)).scalar()
    return (max_inode or 0) + 1


def create_node(db: Session, name: str, node_type: str, parent_id: Optional[int],
                content: str = None, target_path: str = None) -> FilesystemNode:
    """Create a new filesystem node and allocate its blocks."""
    ensure_disk_blocks(db)
    
    # Calculate sizes
    if node_type == "directory":
        size = 64  # empty directory has . and .. (2 * 32 bytes)
    elif node_type == "symlink":
        size = len(target_path.encode()) if target_path else 0
    else:
        size = len(content.encode()) if content else 0

    inode_num = get_next_inode(db)
    
    # Reserve blocks first to check space
    allocate_blocks_for_inode(db, inode_num, size)

    node = FilesystemNode(
        inode_number=inode_num,
        name=name,
        node_type=node_type,
        parent_id=parent_id,
        content=content,
        size_bytes=size,
        target_path=target_path,
        created_at=_utcnow(),
        modified_at=_utcnow(),
        accessed_at=_utcnow(),
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    # Update directory entry counts
    if parent_id:
        recalculate_directory_sizes(db, parent_id)

    return node


def update_file_content(db: Session, node_id: int, new_content: str):
    """Update a file's content and its block allocation. Handles growth/shrinking."""
    node = db.query(FilesystemNode).get(node_id)
    if not node or node.node_type != "file":
        raise ValueError("Node not found or not a file")

    new_size = len(new_content.encode())
    
    # Attempt to allocate/resize blocks
    allocate_blocks_for_inode(db, node.inode_number, new_size)

    node.content = new_content
    node.size_bytes = new_size
    node.modified_at = _utcnow()
    db.commit()
    db.refresh(node)

    if node.parent_id:
        recalculate_directory_sizes(db, node.parent_id)


def delete_node(db: Session, node_id: int) -> bool:
    """Delete a node and all its children recursively, releasing unused blocks."""
    node = db.query(FilesystemNode).get(node_id)
    if node is None:
        return False
    
    parent_id = node.parent_id
    _delete_recursive(db, node)
    db.commit()

    if parent_id:
        recalculate_directory_sizes(db, parent_id)
    return True


def _delete_recursive(db: Session, node: FilesystemNode):
    """Recursively delete children and release blocks when link count drops to 0."""
    children = db.query(FilesystemNode).filter(
        FilesystemNode.parent_id == node.id
    ).all()
    for child in children:
        _delete_recursive(db, child)
        
    inode_num = node.inode_number
    db.delete(node)
    db.flush()

    # Check link count (how many directory entries reference this inode)
    link_count = db.query(FilesystemNode).filter(
        FilesystemNode.inode_number == inode_num
    ).count()

    # If no references remain, free the disk blocks
    if link_count == 0:
        db.query(DiskBlock).filter(DiskBlock.inode_number == inode_num).update(
            {DiskBlock.inode_number: None, DiskBlock.block_index: None}
        )


# ── Hard Links ────────────────────────────────────────────────

def create_hard_link(db: Session, target_node: FilesystemNode,
                      link_name: str, parent_id: int) -> FilesystemNode:
    """Create a hard link sharing the same inode and blocks."""
    link = FilesystemNode(
        inode_number=target_node.inode_number,  # shared inode
        name=link_name,
        node_type="file",
        parent_id=parent_id,
        content=target_node.content,
        size_bytes=target_node.size_bytes,
        created_at=_utcnow(),
        modified_at=_utcnow(),
        accessed_at=_utcnow(),
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    # Recalculate parent directory size
    recalculate_directory_sizes(db, parent_id)
    return link


def create_symlink(db: Session, link_name: str, target_path: str,
                   parent_id: int) -> FilesystemNode:
    """Create a symbolic link."""
    return create_node(db, link_name, "symlink", parent_id, target_path=target_path)


def get_link_count(db: Session, inode_number: int) -> int:
    """Count how many nodes share the same inode number."""
    return db.query(FilesystemNode).filter(
        FilesystemNode.inode_number == inode_number
    ).count()


def resolve_symlink(db: Session, node: FilesystemNode, max_depth: int = 10) -> Optional[FilesystemNode]:
    """Resolve a chain of symlinks with loop prevention."""
    visited = set()
    current = node
    depth = 0
    while current and current.node_type == "symlink" and depth < max_depth:
        if current.id in visited:
            return None  # loop detected
        visited.add(current.id)
        if not current.target_path:
            return None
        current = resolve_path(db, current.target_path)
        depth += 1
    return current


def is_broken_symlink(db: Session, node: FilesystemNode) -> bool:
    """Check if a symlink's target does not resolve."""
    if node.node_type != "symlink":
        return False
    resolved = resolve_path(db, node.target_path) if node.target_path else None
    return resolved is None
