"""CLI for the optional Foody S3/Snowflake RAW foundation."""

import argparse
import json
import os
import sys
from dataclasses import replace

from src.cloud_foundation import (
    CloudConfig,
    plan_sources,
    render_bootstrap,
    run_cloud,
    snowflake_connection,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "bootstrap-sql", "bootstrap", "upload", "run"))
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            sources = plan_sources()
            print(json.dumps({"sources": sources}, indent=2))
            return 0
        config = CloudConfig.from_env()
        if args.command == "bootstrap-sql":
            print(render_bootstrap(config))
            return 0
        if args.command == "bootstrap":
            bootstrap_role = os.getenv("SNOWFLAKE_BOOTSTRAP_ROLE")
            if not bootstrap_role:
                raise ValueError("Set SNOWFLAKE_BOOTSTRAP_ROLE to a permitted admin role")
            admin = replace(config, role=bootstrap_role)
            with snowflake_connection(admin, bootstrap=True) as conn:
                cursor = conn.cursor()
                for statement in render_bootstrap(config).split(";"):
                    if statement.strip():
                        cursor.execute(statement)
            print("Snowflake foundation bootstrap: PASS")
            return 0
        result = run_cloud(config, mode="upload" if args.command == "upload" else "run")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        # SDK exceptions can include credentials or URLs; output only the type.
        print(f"Cloud foundation failed: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
