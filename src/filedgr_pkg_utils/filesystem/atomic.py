import os
import asyncio
import tempfile
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from typing import Generator, AsyncGenerator, Union, IO, Any


@contextmanager
def atomic_write(file_path: Union[str, Path], mode: str = "w", encoding: str = "utf-8", **kwargs) -> Generator[
    IO[Any], None, None]:
    """
    Context manager for atomic file writes.
    Prevents partial file writes in case of application crashes or power failures.

    :param file_path: The target file path.
    :param mode: 'w' for text, 'wb' for binary.
    :param encoding: Default is 'utf-8'. Ignored if mode is binary.
    """
    path = Path(file_path)

    # Ensure the target directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Create a temp file in the SAME directory.
    # This is critical! If the temp file is on a different hard drive or mount point,
    # os.replace will not be atomic.
    fd, temp_path_str = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".tmp-")
    temp_path = Path(temp_path_str)

    # Prepare open() arguments based on binary vs text mode
    open_kwargs = kwargs.copy()
    if "b" not in mode:
        open_kwargs["encoding"] = encoding

    f = open(fd, mode, **open_kwargs)

    try:
        # 2. Yield the file object back to the developer to write their data
        yield f

        # 3. Ensure Python's internal buffers are flushed to the OS
        f.flush()

        # 4. Ensure the OS flushes its buffers to the physical disk platter
        os.fsync(f.fileno())

    except Exception:
        # If the developer's code crashes while writing, close and delete the temp file.
        # The original target file remains 100% untouched and uncorrupted!
        f.close()
        if temp_path.exists():
            temp_path.unlink()
        raise

    else:
        # 5. Close the file and perform the atomic pointer swap
        f.close()
        os.replace(temp_path, path)


# We import aiofiles inside a try/except so the library doesn't crash
# if a developer is only using the synchronous parts and didn't install it.
try:
    import aiofiles
    from aiofiles.threadpool.text import AsyncTextIOWrapper
    from aiofiles.threadpool.binary import AsyncBufferedIOBase

    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False


@asynccontextmanager
async def async_atomic_write(
        file_path: Union[str, Path],
        mode: str = "w",
        encoding: str = "utf-8",
        **kwargs
) -> AsyncGenerator[Union['AsyncTextIOWrapper', 'AsyncBufferedIOBase', Any], None]:
    """
    Async context manager for atomic file writes.
    Prevents event loop blocking and partial file writes.
    """
    if not AIOFILES_AVAILABLE:
        raise ImportError("The 'aiofiles' package is required to use async_atomic_write. Run: pip install aiofiles")

    path = Path(file_path)

    # 1. Offload directory creation to a thread to prevent blocking
    await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)

    # 2. mkstemp interacts with the OS and blocks, so we thread it
    def _create_temp():
        return tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".tmp-")

    fd, temp_path_str = await asyncio.to_thread(_create_temp)
    temp_path = Path(temp_path_str)

    open_kwargs = kwargs.copy()
    if "b" not in mode:
        open_kwargs["encoding"] = encoding

    # 3. Yield the async file object
    try:
        async with aiofiles.open(fd, mode=mode, **open_kwargs) as f:
            yield f

            # Flush aiofiles buffer
            await f.flush()

            # fsync physically flushes to the disk platter (highly blocking!)
            await asyncio.to_thread(os.fsync, fd)

    except Exception:
        # Cleanup temp file on failure
        if await asyncio.to_thread(temp_path.exists):
            await asyncio.to_thread(temp_path.unlink)
        raise

    else:
        # 4. Atomic pointer swap (blocking OS call, offloaded to thread)
        await asyncio.to_thread(os.replace, temp_path, path)
