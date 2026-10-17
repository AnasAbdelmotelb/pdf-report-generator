"""Print the report data as JSON. Usage: python -m scripts.print_report"""
import json

from app.db import connect
from app.report_data import get_report_data

if __name__ == "__main__":
    print(json.dumps(get_report_data(connect()), indent=2))
