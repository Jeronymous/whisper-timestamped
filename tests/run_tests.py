import sys
import unittest

from test_transcribe import *
import test_transcribe

if __name__ == '__main__':

    # Handle several ways of generating expected outputs
    if "--generate" in sys.argv:
        test_transcribe.FAIL_IF_REFERENCE_NOT_FOUND = False
        sys.argv.remove("--generate")
    if "--generate_new" in sys.argv:
        test_transcribe.GENERATE_NEW_ONLY = True
        test_transcribe.FAIL_IF_REFERENCE_NOT_FOUND = False
        sys.argv.remove("--generate_new")
    if "--generate_all" in sys.argv:
        test_transcribe.GENERATE_ALL = True
        test_transcribe.FAIL_IF_REFERENCE_NOT_FOUND = False
        sys.argv.remove("--generate_all")

    unittest.main()
