"""
filesystem.py — API routes for virtual filesystem CRUD, tree operations, and disk block mapping.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FilesystemNode, DiskBlock
from app.schemas import NodeOut, NodeCreate, DiskBlockOut, NodeTree
from app.services.filesystem_service import (
    build_tree, get_node_by_id, create_node, delete_node, get_node_path,
    get_link_count, is_broken_symlink, update_file_content, get_disk_usage,
    TOTAL_BLOCKS, DATA_START_BLOCK
)

router = APIRouter(prefix="/api", tags=["filesystem"])


@router.get("/nodes/tree")
def get_tree(db: Session = Depends(get_db)):
    """Return the full virtual filesystem tree."""
    tree = build_tree(db)
    return tree


@router.get("/nodes/{node_id}")
def get_node(node_id: int, db: Session = Depends(get_db)):
    """Return detailed info for a single node."""
    node = get_node_by_id(db, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    path = get_node_path(db, node)
    link_count = get_link_count(db, node.inode_number)
    broken = is_broken_symlink(db, node) if node.node_type == "symlink" else False

    # Get block numbers allocated to this inode
    blocks = db.query(DiskBlock).filter(
        DiskBlock.inode_number == node.inode_number
    ).order_by(DiskBlock.block_index).all()
    block_numbers = [b.block_number for b in blocks]

    return {
        "id": node.id,
        "inode_number": node.inode_number,
        "name": node.name,
        "node_type": node.node_type,
        "parent_id": node.parent_id,
        "content": node.content,
        "size_bytes": node.size_bytes,
        "target_path": node.target_path,
        "created_at": node.created_at,
        "modified_at": node.modified_at,
        "accessed_at": node.accessed_at,
        "path": path,
        "link_count": link_count,
        "is_broken_symlink": broken,
        "allocated_blocks": block_numbers,
    }


@router.post("/nodes")
def create_fs_node(data: NodeCreate, db: Session = Depends(get_db)):
    """Create a new file, directory or symlink."""
    try:
        node = create_node(
            db,
            name=data.name,
            node_type=data.node_type,
            parent_id=data.parent_id,
            content=data.content,
            target_path=data.target_path,
        )
        return NodeOut.from_orm(node)
    except IOError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/nodes/{node_id}/content")
def update_node_content(node_id: int, data: dict, db: Session = Depends(get_db)):
    """Update file contents."""
    content = data.get("content", "")
    try:
        update_file_content(db, node_id, content)
        return {"message": "Content updated successfully"}
    except IOError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/nodes/{node_id}")
def delete_fs_node(node_id: int, db: Session = Depends(get_db)):
    """Delete a node and its children."""
    success = delete_node(db, node_id)
    if not success:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"message": "Node deleted successfully"}


@router.get("/disk/usage")
def get_disk_usage_endpoint(db: Session = Depends(get_db)):
    """Retrieve virtual disk utilization details."""
    return get_disk_usage(db)


@router.get("/disk/layout")
def get_disk_layout_endpoint(db: Session = Depends(get_db)):
    """
    Return layout showing type/owner of each block.
    Types: superblock (0), inode_table (1-32), data (33-255).
    """
    blocks = db.query(DiskBlock).order_by(DiskBlock.block_number).all()
    layout = []
    
    # Pre-populate map of inode to path/name for details
    inodes = db.query(FilesystemNode).all()
    inode_map = {}
    for node in inodes:
        inode_map[node.inode_number] = {
            "name": node.name,
            "type": node.node_type
        }

    for b in blocks:
        block_num = b.block_number
        if block_num == 0:
            block_type = "superblock"
            detail = "Superblock (FS metadata)"
        elif block_num < DATA_START_BLOCK:
            block_type = "inode_table"
            detail = f"Inode Table (Block {block_num})"
        else:
            if b.inode_number is not None:
                block_type = "allocated_data"
                node_info = inode_map.get(b.inode_number)
                if node_info:
                    detail = f"Inode {b.inode_number}: {node_info['name']} ({node_info['type']}), Index {b.block_index}"
                else:
                    detail = f"Inode {b.inode_number} (orphan entries), Index {b.block_index}"
            else:
                block_type = "free"
                detail = "Free block"
        
        layout.append({
            "block_number": block_num,
            "inode_number": b.inode_number,
            "block_index": b.block_index,
            "block_type": block_type,
            "detail": detail
        })
    return layout
