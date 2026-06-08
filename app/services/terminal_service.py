"""
terminal_service.py — Safe Unix command simulator.
Parses commands from an allowlist and operates on the block-allocated virtual filesystem only.
Never executes shell commands on the host system.
"""

import shlex
from typing import Optional
from sqlalchemy.orm import Session
from app.models import FilesystemNode, DiskBlock
from app.services.filesystem_service import (
    resolve_path, get_root, get_node_path, list_children,
    create_node, delete_node, get_node_by_id, get_link_count,
    create_hard_link, create_symlink, is_broken_symlink, update_file_content, get_disk_usage,
    BLOCK_SIZE
)
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


# Global CWD tracker (since we have no user management, we map to single process/session)
_cwd_id: Optional[int] = None

ALLOWED_COMMANDS = {
    "pwd", "ls", "cd", "mkdir", "touch", "cat", "echo", "rm", "rmdir",
    "ln", "stat", "find", "tree", "clear", "help", "df",
}

HELP_TEXT = """Available Commands:
  pwd             Print working directory
  ls [path]       List directory contents (use -l for details)
  cd <path>       Change directory
  mkdir <name>    Create a directory
  touch <name>    Create or update an empty file
  cat <path>      Display file contents
  echo <text>     Print text (use > file to write, >> file to append)
  rm <path>       Remove a file
  rmdir <path>    Remove an empty directory
  ln <target> <link>   Create a hard link
  ln -s <target> <link> Create a symbolic link
  stat <path>     Display detailed inode and block info
  find <path>     Find files recursively
  tree [path]     Display directory tree structure
  df              Show virtual disk block and space usage
  clear           Clear terminal output
  help            Show this help message
"""


def execute_command(db: Session, command_str: str) -> dict:
    """
    Parse and execute a safe simulated Unix command.
    Returns { "output": str, "cwd": str, "error": bool }.
    """
    command_str = command_str.strip()
    if not command_str:
        return _response(db, "")

    try:
        tokens = shlex.split(command_str)
    except ValueError:
        tokens = command_str.split()

    if not tokens:
        return _response(db, "")

    cmd = tokens[0].lower()
    args = tokens[1:]

    if cmd not in ALLOWED_COMMANDS:
        return _response(db, f"unixguard: command not found: {cmd}\nType 'help' for available commands.", error=True)

    # Dispatch
    handlers = {
        "pwd": _cmd_pwd,
        "ls": _cmd_ls,
        "cd": _cmd_cd,
        "mkdir": _cmd_mkdir,
        "touch": _cmd_touch,
        "cat": _cmd_cat,
        "echo": _cmd_echo,
        "rm": _cmd_rm,
        "rmdir": _cmd_rmdir,
        "ln": _cmd_ln,
        "stat": _cmd_stat,
        "find": _cmd_find,
        "tree": _cmd_tree,
        "df": _cmd_df,
        "clear": _cmd_clear,
        "help": _cmd_help,
    }

    handler = handlers.get(cmd)
    try:
        output, error = handler(db, args)
    except IOError as ioe:
        output, error = f"IO Error: {str(ioe)}", True
    except Exception as e:
        output, error = f"Error: {str(e)}", True

    return _response(db, output, error)


def _response(db: Session, output: str, error: bool = False) -> dict:
    cwd_id = _get_cwd_id(db)
    cwd_node = get_node_by_id(db, cwd_id)
    cwd_path = get_node_path(db, cwd_node) if cwd_node else "/"
    return {"output": output, "cwd": cwd_path, "error": error}


def _get_cwd_id(db: Session) -> int:
    global _cwd_id
    if _cwd_id is None:
        root = get_root(db)
        _cwd_id = root.id if root else 1
    return _cwd_id


def _resolve(db: Session, path: str) -> Optional[FilesystemNode]:
    cwd_id = _get_cwd_id(db)
    return resolve_path(db, path, cwd_id)


# ── Command Implementations ──────────────────────────────────

def _cmd_pwd(db, args):
    cwd_id = _get_cwd_id(db)
    node = get_node_by_id(db, cwd_id)
    return get_node_path(db, node) if node else "/", False


def _cmd_ls(db, args):
    long_format = False
    path = None

    for arg in args:
        if arg in ("-l", "-la", "-al"):
            long_format = True
        else:
            path = arg

    target = _resolve(db, path) if path else get_node_by_id(db, _get_cwd_id(db))

    if target is None:
        return f"ls: cannot access '{path}': No such file or directory", True

    if target.node_type != "directory":
        if long_format:
            return _format_long_entry(db, target), False
        return target.name, False

    children = list_children(db, target.id)
    if not children:
        return "", False

    if long_format:
        lines = [_format_long_entry(db, c) for c in children]
        return "\n".join(lines), False
    else:
        names = []
        for c in children:
            if c.node_type == "directory":
                names.append(f"\033[1;34m{c.name}/\033[0m")
            elif c.node_type == "symlink":
                names.append(f"\033[1;36m{c.name}@\033[0m")
            else:
                names.append(c.name)
        return "  ".join(names), False


def _format_long_entry(db, node):
    type_char = "d" if node.node_type == "directory" else ("l" if node.node_type == "symlink" else "-")
    link_count = get_link_count(db, node.inode_number)
    size = str(node.size_bytes).rjust(6)
    
    # Calculate blocks allocated to this inode
    blocks = db.query(DiskBlock).filter(DiskBlock.inode_number == node.inode_number).count()
    block_info = f" {blocks} blks".rjust(9)

    mod = node.modified_at.strftime("%b %d %H:%M") if node.modified_at else "Jan 01 00:00"
    name = node.name
    if node.node_type == "symlink" and node.target_path:
        name += f" -> {node.target_path}"
    return f"{type_char} {link_count} {size}B {block_info} {mod} {name}"


def _cmd_cd(db, args):
    global _cwd_id
    if not args:
        root = get_root(db)
        _cwd_id = root.id
        return "", False

    target = _resolve(db, args[0])
    if target is None:
        return f"cd: no such file or directory: {args[0]}", True
    if target.node_type != "directory":
        return f"cd: not a directory: {args[0]}", True

    _cwd_id = target.id
    return "", False


def _cmd_mkdir(db, args):
    if not args:
        return "mkdir: missing operand", True

    name = args[0]
    if "/" in name:
        parts = name.rsplit("/", 1)
        parent = _resolve(db, parts[0])
        dir_name = parts[1]
    else:
        parent = get_node_by_id(db, _get_cwd_id(db))
        dir_name = name

    if parent is None or parent.node_type != "directory":
        return f"mkdir: cannot create directory '{name}': No such parent directory", True

    existing = db.query(FilesystemNode).filter(
        FilesystemNode.parent_id == parent.id,
        FilesystemNode.name == dir_name,
    ).first()
    if existing:
        return f"mkdir: cannot create directory '{dir_name}': File exists", True

    create_node(db, dir_name, "directory", parent.id)
    return "", False


def _cmd_touch(db, args):
    if not args:
        return "touch: missing file operand", True

    name = args[0]
    if "/" in name:
        parts = name.rsplit("/", 1)
        parent = _resolve(db, parts[0])
        fname = parts[1]
    else:
        parent = get_node_by_id(db, _get_cwd_id(db))
        fname = name

    if parent is None or parent.node_type != "directory":
        return f"touch: cannot touch '{name}': No such directory", True

    existing = db.query(FilesystemNode).filter(
        FilesystemNode.parent_id == parent.id,
        FilesystemNode.name == fname,
    ).first()
    if existing:
        existing.accessed_at = _utcnow()
        existing.modified_at = _utcnow()
        db.commit()
        return "", False

    create_node(db, fname, "file", parent.id)
    return "", False


def _cmd_cat(db, args):
    if not args:
        return "cat: missing file operand", True

    target = _resolve(db, args[0])
    if target is None:
        return f"cat: {args[0]}: No such file or directory", True
    if target.node_type == "directory":
        return f"cat: {args[0]}: Is a directory", True
    if target.node_type == "symlink":
        if is_broken_symlink(db, target):
            return f"cat: {args[0]}: Broken symbolic link -> {target.target_path}", True
        target = _resolve(db, target.target_path)
        if target is None:
            return f"cat: {args[0]}: Broken symbolic link", True

    target.accessed_at = _utcnow()
    db.commit()
    return target.content or "", False


def _cmd_echo(db, args):
    if not args:
        return "", False

    # Check for redirection: > (overwrite) or >> (append)
    redirect_mode = None
    if ">" in args:
        redirect_mode = ">"
        idx = args.index(">")
    elif ">>" in args:
        redirect_mode = ">>"
        idx = args.index(">>")

    if redirect_mode:
        text = " ".join(args[:idx])
        if idx + 1 < len(args):
            filepath = args[idx + 1]
            target = _resolve(db, filepath)
            
            if target and target.node_type == "file":
                if redirect_mode == ">":
                    new_content = text
                else:
                    new_content = (target.content or "") + ("\n" if target.content else "") + text
                update_file_content(db, target.id, new_content)
                return "", False
            elif target is None:
                # Create file and write content
                if "/" in filepath:
                    parts = filepath.rsplit("/", 1)
                    parent = _resolve(db, parts[0])
                    fname = parts[1]
                else:
                    parent = get_node_by_id(db, _get_cwd_id(db))
                    fname = filepath
                if parent:
                    create_node(db, fname, "file", parent.id, content=text)
                    return "", False
            return f"echo: cannot write to '{filepath}'", True
        return text, False

    return " ".join(args), False


def _cmd_rm(db, args):
    if not args:
        return "rm: missing operand", True

    target = _resolve(db, args[0])
    if target is None:
        return f"rm: cannot remove '{args[0]}': No such file or directory", True
    if target.node_type == "directory":
        return f"rm: cannot remove '{args[0]}': Is a directory (use rmdir)", True
    if target.name == "/":
        return "rm: cannot remove root directory", True

    delete_node(db, target.id)
    return "", False


def _cmd_rmdir(db, args):
    if not args:
        return "rmdir: missing operand", True

    target = _resolve(db, args[0])
    if target is None:
        return f"rmdir: failed to remove '{args[0]}': No such directory", True
    if target.node_type != "directory":
        return f"rmdir: failed to remove '{args[0]}': Not a directory", True

    children = list_children(db, target.id)
    if children:
        return f"rmdir: failed to remove '{args[0]}': Directory not empty", True

    delete_node(db, target.id)
    return "", False


def _cmd_ln(db, args):
    symbolic = False
    remaining = list(args)

    if "-s" in remaining:
        symbolic = True
        remaining.remove("-s")

    if len(remaining) < 2:
        return "ln: missing operand\nUsage: ln [-s] <target> <link_name>", True

    target_path = remaining[0]
    link_name = remaining[1]

    # Resolve parent for new link
    if "/" in link_name:
        parts = link_name.rsplit("/", 1)
        parent = _resolve(db, parts[0])
        lname = parts[1]
    else:
        parent = get_node_by_id(db, _get_cwd_id(db))
        lname = link_name

    if parent is None:
        return f"ln: failed to create link '{link_name}': Parent not found", True

    if symbolic:
        create_symlink(db, lname, target_path, parent.id)
        return "", False
    else:
        target = _resolve(db, target_path)
        if target is None:
            return f"ln: failed to access '{target_path}': No such file", True
        if target.node_type == "directory":
            return "ln: hard link not allowed for directory", True
        create_hard_link(db, target, lname, parent.id)
        return "", False


def _cmd_stat(db, args):
    if not args:
        return "stat: missing operand", True

    target = _resolve(db, args[0])
    if target is None:
        return f"stat: cannot stat '{args[0]}': No such file or directory", True

    path = get_node_path(db, target)
    lc = get_link_count(db, target.inode_number)
    
    # Query blocks
    blocks = db.query(DiskBlock).filter(DiskBlock.inode_number == target.inode_number).order_by(DiskBlock.block_index).all()
    block_nums = [str(b.block_number) for b in blocks]
    blocks_str = ", ".join(block_nums) if block_nums else "None"

    lines = [
        f"  File: {path}",
        f"  Size: {target.size_bytes} Bytes\tBlocks: {len(blocks)}\tIO Block: {BLOCK_SIZE}\t{target.node_type}",
        f"Device: virtual\tInode: {target.inode_number}\tLinks: {lc}",
        f"Blocks Map: [{blocks_str}]",
        f"Access: {target.accessed_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Modify: {target.modified_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Create: {target.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if target.node_type == "symlink":
        broken = " [BROKEN]" if is_broken_symlink(db, target) else " [OK]"
        lines.insert(1, f"  Link: -> {target.target_path}{broken}")

    return "\n".join(lines), False


def _cmd_find(db, args):
    path = args[0] if args else "."
    target = _resolve(db, path)
    if target is None:
        return f"find: '{path}': No such file or directory", True

    results = []
    _find_recursive(db, target, get_node_path(db, target), results)
    return "\n".join(results) if results else "(empty)", False


def _find_recursive(db, node, current_path, results):
    results.append(current_path)
    if node.node_type == "directory":
        for child in list_children(db, node.id):
            child_path = current_path.rstrip("/") + "/" + child.name
            _find_recursive(db, child, child_path, results)


def _cmd_tree(db, args):
    path = args[0] if args else "."
    target = _resolve(db, path)
    if target is None:
        return f"tree: '{path}': No such file or directory", True

    lines = []
    _tree_recursive(db, target, "", True, lines)
    return "\n".join(lines), False


def _tree_recursive(db, node, prefix, is_last, lines):
    connector = "└── " if is_last else "├── "
    type_indicator = ""
    if node.node_type == "directory":
        type_indicator = "/"
    elif node.node_type == "symlink":
        type_indicator = f" -> {node.target_path}"

    if not lines:
        lines.append(node.name + type_indicator)
    else:
        lines.append(prefix + connector + node.name + type_indicator)

    if node.node_type == "directory":
        children = list_children(db, node.id)
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(children):
            _tree_recursive(db, child, child_prefix, i == len(children) - 1, lines)


def _cmd_df(db, args):
    usage = get_disk_usage(db)
    lines = [
        "Filesystem    Size    Used    Free   Use%   Type",
        f"vdisk0       {usage['total_space_bytes']/1024:.1f}K   {usage['used_space_bytes']/1024:.1f}K   {usage['free_space_bytes']/1024:.1f}K   {usage['used_blocks']/usage['total_blocks']*100:.0f}%   ext2"
    ]
    return "\n".join(lines), False


def _cmd_clear(db, args):
    return "\x1b[CLEAR]", False


def _cmd_help(db, args):
    return HELP_TEXT, False
