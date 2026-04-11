"""Virtual filesystem sandbox (ephemeral until `hex merge` to host disk)."""

from fs.memoryfs import MemoryFS


def make_memory_sandbox() -> MemoryFS:
    return MemoryFS()
