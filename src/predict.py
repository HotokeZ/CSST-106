"""Single-image prediction uses the same entry point as batch runs."""
from run import main

if __name__ == "__main__":
    raise SystemExit(main())
