from __future__ import annotations

import logging

from dotenv import load_dotenv

from pipeline import ResearchPipeline, build_arg_parser, config_from_args


def main() -> int:
    load_dotenv("config.env")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler("logs/platform.log", encoding="utf-8"), logging.StreamHandler()],
    )
    parser = build_arg_parser()
    args = parser.parse_args()
    result = ResearchPipeline(config_from_args(args)).run()
    for name, path in result["written"].items():
        logging.info("wrote %s -> %s", name, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
