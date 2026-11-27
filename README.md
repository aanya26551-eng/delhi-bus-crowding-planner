# Crowdedness-Aware Journey Planner (Delhi Bus — Phase 1 Prototype)

## Overview
Delhi bus commuters often deal with heavily crowded buses where boarding is difficult and standing space is tight, while standard journey planners rank options mostly by travel time and transfers. This Phase 1 prototype processes October 2026 Delhi ETM and e-ticketing records to estimate route- and hour-level bus crowding and presents it through a **Commuter Journey Planner** and a **Bus Operator & Planner View**.

## Repository Structure
- `app.py`: Interactive Streamlit web application featuring a Commuter Journey Planner (departure hour, weekday/weekend toggle, comfort vs. speed priority, crowding badges, and sample-size reliability flags) and a Bus Operator & Planner View (hourly load curve against crowding thresholds and top overloaded route-hours).
- `pipeline.py`: Reproducible Python pipeline that downloads/extracts the October 2026 Delhi ticketing dataset, aggregates passenger counts by route, hour, and weekday/weekend, estimates bus loads and crowding tiers, flags low-sample estimates, and outputs `crowding_summary.json` and `crowding_summary.csv`.
- `crowding_summary.json`: Aggregated summary artifact generated from the ticket dataset (with a built-in baseline fallback in `app.py` when run standalone without the summary file).
- `requirements.txt`: Python package dependencies for the app and pipeline.

## How to Run & Reproduce
1. **Run the Data Pipeline (Google Colab or local Python 3.10+):**
   ```bash
   pip install pandas numpy
   python pipeline.py
