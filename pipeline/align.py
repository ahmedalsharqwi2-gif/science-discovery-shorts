"""CLI compatibility entry point for measured forced alignment."""
import sys
from forced_align import main
if __name__ == "__main__":
    sys.exit(main(sys.argv[1],sys.argv[2]))
