try:
    from .local_projections import main
except ImportError:
    from local_projections import main


if __name__ == "__main__":
    main()
