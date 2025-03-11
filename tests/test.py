from ctypes import *
import pytest
import platform
import re

HASH_ERROR_OK = 0
HASH_ERROR_EXCEPTION = 1
HASH_ERROR_ALREADY_INITIALIZED = 2
HASH_ERROR_ARGUMENT_NULL = 3
HASH_ERROR_ARGUMENT_INVALID = 4
HASH_ERROR_MEMORY = 5
HASH_ERROR_LOG_EMPTY = 6
HASH_ERROR_NOT_INITIALIZED = 7

OPERATION_ID = c_size_t(0)
dll_path = "../bin/"
if platform.system() == "Linux":
    dll_path = f"{dll_path}linux/libhash.so"
elif platform.system() == "Windows":
    dll_path = f"{dll_path}windows/hash.dll"
elif platform.system() == "Darwin":
    dll_path = f"{dll_path}mac/libhash.dylib"
else:
    raise Exception("Unsupported platform")

log_line_pattern = re.compile(r"^[a-zA-Z0-9]+ (\S+) ([a-fA-F\d]{32})$")

my_dll = CDLL(dll_path)

my_dll.HashInit.argtypes = []
my_dll.HashInit.restype = c_uint32

my_dll.HashTerminate.argtypes = []
my_dll.HashTerminate.restype = c_uint32

my_dll.HashDirectory.argtypes = [c_char_p, POINTER(c_size_t)]
my_dll.HashDirectory.restype = c_uint32

my_dll.HashReadNextLogLine.argtypes = [POINTER(c_char_p)]
my_dll.HashReadNextLogLine.restype = c_uint32

my_dll.HashStatus.argtypes = [c_size_t, POINTER(c_bool)]
my_dll.HashStatus.restype = c_uint32

my_dll.HashStop.argtypes = [c_size_t]
my_dll.HashStop.restype = c_uint32

my_dll.HashFree.argtypes = [c_void_p]

TEST_DIRS = ["./testFiles1", "./testFiles2"]


def wait_for_hash_status(operation_id: c_size_t):
    """Wait for hashStatus to be False

    Keyword arguments:
    operation_id -- operation which should be waited for
    """
    flag = c_bool(True)
    while flag.value:
        my_dll.HashStatus(operation_id, byref(flag))


def get_operation_id() -> c_size_t:
    """Returns increments OPERATION_ID"""
    OPERATION_ID.value += 1
    return OPERATION_ID


def verify_log_line_format(log_line: str) -> bool:
    """returns if log line pattern is correct"""
    return bool(log_line_pattern.match(log_line))


@pytest.fixture
def setup_library():
    """Initialize and terminate the library in a test setup."""
    init_status = my_dll.HashInit()
    assert (
        init_status == HASH_ERROR_OK
    ), f"Failed to initialize the library, error code: {init_status}"

    yield 

    terminate_status = my_dll.HashTerminate()
    assert (
        terminate_status == HASH_ERROR_OK
    ), f"Failed to terminate the library, error code: {terminate_status}"


def test_hash_init_and_terminate(setup_library):
    """Test the initialization and termination of the library."""
    pass


def test_hash_init_multiple_times(setup_library):
    """Test the initialization of the library multiple times."""
    init_status = my_dll.HashInit()
    assert (
        init_status == HASH_ERROR_ALREADY_INITIALIZED
    ), f"Library already initialized error did not occure, error code: {init_status}"


def test_hash_terminate_without_init(setup_library):
    """Test library termination without initialiation"""
    test_dll = CDLL(dll_path)

    test_dll.HashTerminate.argtypes = []
    test_dll.HashTerminate.restype = c_uint32

    init_status = my_dll.HashTerminate()
    assert (
        init_status == HASH_ERROR_NOT_INITIALIZED
    ), f"Library not initialized error did not occure, error code: {init_status}"


def test_hash_directory(setup_library):
    """Test hashing a directory."""
    operation_id = get_operation_id()
    result = my_dll.HashDirectory(TEST_DIRS[0].encode("utf-8"), byref(operation_id))
    assert result == HASH_ERROR_OK, f"HashDirectory failed with error code: {result}"

    wait_for_hash_status(operation_id)


def test_hash_read_next_log_line(setup_library):
    """Test reading the next log line."""
    operation_id = get_operation_id()
    my_dll.HashDirectory(TEST_DIRS[0].encode("utf-8"), byref(operation_id))
    wait_for_hash_status(operation_id)

    hash_log = c_char_p()
    result = my_dll.HashReadNextLogLine(byref(hash_log))
    assert (
        result == HASH_ERROR_OK or result == HASH_ERROR_LOG_EMPTY
    ), f"HashReadNextLogLine failed with error code: {result}"

    if result == HASH_ERROR_OK:
        my_dll.HashFree(hash_log)


def test_hash_status(setup_library):
    """Test the status of an operation."""
    operation_id = get_operation_id()

    my_dll.HashDirectory(TEST_DIRS[0].encode("utf-8"), byref(operation_id))
    running_flag = c_bool(False)
    result = my_dll.HashStatus(operation_id, byref(running_flag))
    assert result == HASH_ERROR_OK, f"HashStatus failed with error code: {result}"
    wait_for_hash_status(operation_id)


def test_log_line_format(setup_library):
    """Test log line format using regex"""
    operation_id = get_operation_id()
    my_dll.HashDirectory(TEST_DIRS[0].encode("utf-8"), byref(operation_id))
    wait_for_hash_status(operation_id)

    hash_log = c_char_p()
    my_dll.HashReadNextLogLine(byref(hash_log))
    log_line = hash_log.value.decode("utf-8")
    assert verify_log_line_format(log_line), f"log line format is invalid: {log_line}"

    my_dll.HashFree(hash_log)


def test_hash_stop(setup_library):
    """Test stopping an operation."""
    operation_id = get_operation_id()
    my_dll.HashDirectory(TEST_DIRS[0].encode("utf-8"), byref(operation_id))
    result = my_dll.HashStop(operation_id)
    assert result == HASH_ERROR_OK, f"HashStop failed with error code: {result}"

    running_flag = c_bool(False)
    assert (
        my_dll.HashStatus(operation_id, byref(running_flag)) == HASH_ERROR_OK
    ), f"HashStatus failed with error code: {result}"


def test_hash_free(setup_library):
    """Test the HashFree function."""
    hash_pointer = c_void_p()
    my_dll.HashFree(hash_pointer)


def test_hash_read_next_log_line(setup_library):
    """Test reading the next log line."""
    operation_id = get_operation_id()
    my_dll.HashDirectory(TEST_DIRS[0].encode("utf-8"), byref(operation_id))
    my_dll.HashDirectory(TEST_DIRS[1], byref(operation_id))
    wait_for_hash_status(operation_id)

    hash_log = c_char_p()
    while my_dll.HashReadNextLogLine(byref(hash_log)) == HASH_ERROR_OK:
        my_dll.HashFree(hash_log)
        assert verify_log_line_format(
            hash_log
        ), f"HashReadNextLogLine failed to write log line in correct format when running multiple times: {hash_log}"
