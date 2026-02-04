# 🏎️ F1 Data Analysis Dashboard

**Course:** BIU DS22 - Python Class
**Project Type:** Final Assignment

## 📌 Project Overview
This project is a Python-based data science tool designed to analyze and visualize Formula 1 telemetry data.
By leveraging the **OpenF1 API**, the application processes raw racing data to provide deep insights into driver performance, enabling users to compare speed, throttle application, and braking points across different drivers and sessions.

## 🚀 Live Demo
Click below to access the deployed application on Streamlit Cloud:
👉 **[https://ziv8incredible8app.streamlit.app/](https://ziv8incredible8app.streamlit.app/)**

## ✨ Key Features
* **Driver Comparison:** Overlay car data traces (Speed vs. Distance) of two drivers simultaneously.
* **Real-Time/Historical Data:** Fetch data from any session available in the OpenF1 database.
* **Interactive Visualization:** Dynamic charts powered by **Plotly** and **Streamlit**.
* **Data Synchronization:** Algorithms to align low-frequency GPS data with high-frequency car data.

## 🛠️ Installation & Setup
This project uses **Poetry** for dependency management to ensure a reproducible environment.

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/ZD-MEC/PythonProject2.git](https://github.com/ZD-MEC/PythonProject2.git)
    cd PythonProject2
    ```

2.  **Install dependencies using Poetry:**
    Ensure you have Poetry installed. Then run:
    ```bash
    poetry install
    ```
    *This will read `pyproject.toml` and `poetry.lock` to install the exact package versions.*

## ▶️ How to Run
The entry point for this application is `main.py`.

To launch the dashboard locally, execute the following command inside the project directory:

```bash
poetry run streamlit run main.py

