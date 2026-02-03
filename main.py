import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from DataProcessor import DataProcessor
from F1_API_importer import F1_API
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# 1. Page Configuration
st.set_page_config(page_title="F1 Analytics", layout="wide")

st.title("F1 Analytics App 🏎️")
st.markdown("Analyze F1 data for specific Drivers and Races")

# 2. Sidebar - User Inputs
# We put inputs in the sidebar to keep the main view clean
with st.sidebar:
  st.header("Session Settings")


  selected_year = st.selectbox("Select Year", options= ['2023', '2024'])
  df_session = F1_API.get_sessions(selected_year)

  selected_country = st.selectbox("Select Country", options= df_session['country_name'].unique() )
  df_filtered_country = df_session[df_session['country_name'] == selected_country]
  valid_races = df_filtered_country[df_filtered_country['session_name'].str.contains('Race|Qualifying', case=False)]
  selected_race = st.selectbox("Select Race", options=  valid_races['session_name'].unique())
  session_row = valid_races[valid_races['session_name'] == selected_race]
  session_key = int(session_row['session_key'].iloc[0])

  # 3. Load Drivers for this session
  df_driver = F1_API.get_drivers(session_key)

  #protection against crash
  if df_driver.empty or 'full_name' not in df_driver.columns:
    st.warning("⚠️ No driver data available for this specific session via OpenF1 API.")
    st.stop()

    # Sort the unique driver names alphabetically
  sorted_driver_list = sorted(df_driver['full_name'].unique())
  selected_driver = st.selectbox("Select Driver", options=sorted_driver_list)
  # Get the driver number based on the selection
  driver_number = df_driver.loc[df_driver['full_name'] == selected_driver, 'driver_number'].iloc[0]
  #lap_df, date_start_session = F1_API.get_laps(session_key, driver_number)

  st.markdown("---")
  st.markdown("### ⚔️ Compare Drivers")

# Removing the selected driver to avoid duplicates
  available_drivers = sorted(df_driver[df_driver['full_name'] != selected_driver]['full_name'].unique())

  comparison_names = st.multiselect(
    "Select rivals (Max 2)",
    options=available_drivers,
    max_selections=2
  )

  st.markdown("---")

  # The Button!
  # The app waits here until the user clicks this button
  run_btn=st.button("Load Data")

# --- 3. Main Logic Flow ---

if run_btn:
  # Fetching data
  race_df = DataProcessor.get_merged_race_data(session_key, driver_number)
  positions_df = DataProcessor.get_position_data(session_key)
  laps_data, dates_data = DataProcessor.get_race_positions(session_key)

  # Save to session state
  st.session_state['race_data'] = race_df
  st.session_state['positions_data'] = positions_df
  st.session_state['laps_data'] = laps_data
  st.session_state['dates_data'] = dates_data



  comp_data = {}

  if comparison_names:
    for comp_driver_name in comparison_names:

      comp_num = df_driver.loc[df_driver['full_name'] == comp_driver_name, 'driver_number'].iloc[0]
      comp_race_df = DataProcessor.get_merged_race_data(session_key, comp_num)


      if not comp_race_df.empty:
        comp_data[comp_driver_name] = comp_race_df

  st.session_state['comp_data'] = comp_data

if not run_btn:
  # Displayed when no data is loaded yet
  st.divider()

  # 1. Hero Section with Image
  # Using a high-quality F1 related placeholder or local image

  st.markdown("""
    #### Ready to analyze?

    This dashboard provides data and insights for Formula 1 Races. 
    To get started, please use the **sidebar on the left**:
    """)

  # 2. Feature Showcase (3 Columns)
  col1, col2, col3 = st.columns(3)

  with col1:
    st.markdown("#### 📉 Car data")
    st.markdown("Compare speed, throttle, and brake traces lap-by-lap.")

  with col2:
    st.markdown("#### 🗺️ Track Map")
    st.markdown("Visualize driver lines and corner speeds on the actual circuit.")

  with col3:
    st.markdown("#### ⚔️ Rivals")
    st.markdown("Head-to-head comparison between any two drivers.")

  # 3. Call to Action (Instruction)
  st.info("👈  Select a Year, Country, and Driver in the sidebar to begin.")

# --- 4. Visualization Logic (Runs on every reload/slider move) ---

# Check if we have data in memory
if 'race_data' in st.session_state and 'positions_data' in st.session_state:

  # Retrieve data from "The Backpack" (Session State)
  race_df = st.session_state['race_data']
  positions_df = st.session_state['positions_data']
  laps_data = st.session_state['laps_data']
  dates_data = st.session_state['dates_data']

# --- 3. Main Logic Flow: Data Loading ---
if run_btn:
  # Fetching data
  # We fetch all necessary datasets at once when the button is clicked
  race_df = DataProcessor.get_merged_race_data(session_key, driver_number)
  positions_df = DataProcessor.get_position_data(session_key)
  laps_data, dates_data = DataProcessor.get_race_positions(session_key)

  # Save to session state ("The Backpack")
  st.session_state['race_data'] = race_df
  st.session_state['positions_data'] = positions_df
  st.session_state['laps_data'] = laps_data
  st.session_state['dates_data'] = dates_data

  # Logic for loading comparison drivers
  comp_data = {}
  if comparison_names:
    for comp_driver_name in comparison_names:
      # Find the driver number based on the name
      comp_num = df_driver.loc[df_driver['full_name'] == comp_driver_name, 'driver_number'].iloc[0]
      comp_race_df = DataProcessor.get_merged_race_data(session_key, comp_num)

      if not comp_race_df.empty:
        comp_data[comp_driver_name] = comp_race_df

  st.session_state['comp_data'] = comp_data

# --- 4. Visualization Logic (Runs on every reload/slider move) ---

# Check if we have data in memory before trying to plot
if 'race_data' in st.session_state and 'positions_data' in st.session_state:

  # Retrieve data from Session State
  race_df = st.session_state['race_data']
  positions_df = st.session_state['positions_data']
  laps_data = st.session_state['laps_data']
  dates_data = st.session_state['dates_data']

  if not race_df.empty:

    if not race_df.empty:
      #st.success("✅ Data Loaded Successfully!")

      # =========================================================
      # 1. SESSION INSIGHTS (Global Race Stats)
      # =========================================================

      # Calculate stats
      fastest_lap = DataProcessor.get_session_fastest_lap(session_key)
      race_stats = DataProcessor.get_session_summary_stats(session_key)

      st.markdown("### 🏆 Race Highlights")

      # Row 1: Winner & Fastest Lap, Highlights using standard Markdown for better font control
      col_h1, col_h2, col_h3, col_h4 = st.columns(4)

      # 1. Winner
      with col_h1:
        st.caption("🥇 Winner")
        # Using markdown headers (#####) makes text smaller than st.metric but still bold
        st.markdown(f"##### {race_stats.get('winner', 'N/A')}")

      # 2. Highest Climber
      with col_h2:
        st.caption("🚀 Highest Climber")
        mover_name = race_stats.get('mover_name', 'N/A')
        gain = race_stats.get('mover_gain', 0)

        # Display Name
        st.markdown(f"##### {mover_name}")

        # Display Gain in Green if positive
        if gain > 0:
          st.markdown(f":green[▲ {gain} Positions]")
        else:
          st.markdown("No Change")

      # 3. DNFs
      with col_h3:
        st.caption("❌ DNFs")
        dnf_count = race_stats.get('dnf_count', 0)
        st.markdown(f"##### {dnf_count} Drivers")
        # Use an expander or help tooltip for details to keep UI clean
        if dnf_count > 0:
          st.markdown(f"_{race_stats.get('dnf_names', '')}_")

      # 4. Fastest Lap
      with col_h4:
        st.caption("⚡ Fastest Lap")
        if fastest_lap:
          st.markdown(f"##### {fastest_lap['time']}")
          st.markdown(f"_{fastest_lap['driver']}_")
        else:
          st.markdown("##### N/A")

      st.markdown("---")

      # =========================================================
      # 2. DRIVER SPECIFIC STATS (Selected Driver)
      # =========================================================
      st.markdown(f"### 📊 Stats for {selected_driver}")

      # --- Top Metrics Row  ---
      # 1. Fetch accurate time (race_df is telemetry, so we use F1_API for timing)
      laps_official, _ = F1_API.get_laps(session_key, driver_number)
      best_lap_str = str(laps_official['lap_duration'].min()).split('days ')[-1][:-3]

      # 2. Calculate Positions (Extracting directly from your existing positions_df)
      d_pos = positions_df[positions_df['full_name'] == selected_driver]
      # We filter assuming 'type' contains 'Grid'/'Start' for start and 'Finish'/'Race' for end
      p_start = d_pos[d_pos['type'].str.contains('Grid|Start', case=False)]['position'].min()
      p_finish = d_pos[d_pos['type'].str.contains('Finish|Race', case=False)]['position'].min()
      p_change = int(p_start - p_finish)  # Positive = Improvement

      # 3. Display Metrics
      m1, m2, m3, m4 = st.columns(4)
      m1.metric("Top Speed", f"{race_df['speed'].max()} km/h")
      m2.metric("Fastest Lap", best_lap_str)
      m3.metric("Finish Pos", f"P{int(p_finish)}")
      m4.metric("Pos Change", p_change, delta=p_change)

      st.divider()  # Visual separation

    # --- The Tabs Architecture ---
      # ---------------------------------------------------------
      # Safety Check: Ensure driver has enough laps to visualize
      # ---------------------------------------------------------
      max_lap = int(race_df['lap_number'].max())

      if max_lap <= 1:
        # Scenario: Driver retired on Lap 1 or data is insufficient for a slider
        st.warning(f"⚠️ Insufficient telemetry data for {selected_driver}. The driver likely retired on the first lap.")

      else:
        # Proceed with Tabs and Visualization only if we have valid data

        # --- The Tabs Architecture ---
        tab_telemetry, tab_overview, tab_compare = st.tabs(
          ["📉 Car data Deep Dive", "🏁 Race Overview", "⚔️ Head-to-Head"])

        # === TAB 1: TELEMETRY (The slider lives here) ===
        with tab_telemetry:
          st.subheader("Lap-by-Lap Analysis")

          # 1. The Slider (Now safe because max_lap > 1)
          selected_lap = st.slider("Select Lap", min_value=1, max_value=max_lap, value=1)

          # 2. Filter Data (Fast in-memory operation)
          subset = race_df[race_df['lap_number'] == selected_lap]

          # 3. Split View (Map vs Graph)
          col_map, col_graph = st.columns([1, 1])  # 1:1 ratio

          with col_map:
            st.markdown("**Track Map** (Speed Visualization)")

            # Renaming columns for clearer tooltip
            map_df = subset.rename(columns={'x': 'X_coordinate', 'y': 'Y_coordinate'})

            # Using Scatter to allow coloring by speed
            fig_map = px.scatter(
              map_df,
              x='X_coordinate',
              y='Y_coordinate',
              color='speed',
              color_continuous_scale='Turbo',
              hover_data=['speed', 'Total_distance', 'throttle', 'rpm', 'n_gear', 'brake']
            )
            # Keep aspect ratio fixed so the track doesn't look distorted
            fig_map.update_yaxes(scaleanchor="x", scaleratio=1)
            fig_map.update_layout(xaxis_visible=False, yaxis_visible=False)  # Hide axes for cleaner map
            st.plotly_chart(fig_map, use_container_width=True)

          with col_graph:
            # 1. Create the Subplots structure (5 rows, sharing X axis)
            fig_tel = make_subplots(
              rows=5, cols=1,
              shared_xaxes=True,  # Critical: Zooming one zooms all
              vertical_spacing=0.06,  # Gap between charts
              row_heights=[0.3, 0.15, 0.15, 0.2, 0.2],  # Speed gets more space
              subplot_titles=("Speed (km/h)", "RPM", "Gear (num)", "Throttle (%)", "Brake (Y/N)")
            )

            # --- Trace 1: Speed (Blue) ---
            fig_tel.add_trace(
              go.Scatter(x=subset['Total_distance'], y=subset['speed'], name='Speed', line=dict(color='cyan', width=2)),
              row=1, col=1
            )

            # --- Trace 2: RPM (Yellow) ---
            fig_tel.add_trace(
              go.Scatter(x=subset['Total_distance'], y=subset['rpm'], name='RPM', line=dict(color='yellow', width=1)),
              row=2, col=1
            )

            # --- Trace 3: Gear (White Step Line) ---
            fig_tel.add_trace(
              go.Scatter(x=subset['Total_distance'], y=subset['n_gear'], name='Gear',
                         line=dict(color='white', width=1.5),
                         line_shape='hv'),
              row=3, col=1
            )

            # --- Trace 4: Throttle (Green Area) ---
            fig_tel.add_trace(
              go.Scatter(x=subset['Total_distance'], y=subset['throttle'], name='Throttle',
                         line=dict(color='lime', width=1), fill='tozeroy'),
              row=4, col=1
            )

            # --- Trace 5: Brake (Red Area) ---
            fig_tel.add_trace(
              go.Scatter(x=subset['Total_distance'], y=subset['brake'], name='Brake', line=dict(color='red', width=1),
                         fill='tozeroy'),
              row=5, col=1
            )

            # Layout Polish
            fig_tel.update_layout(
              height=800,
              showlegend=False,
              hovermode="x unified",
              margin=dict(l=0, r=0, t=20, b=0),
              paper_bgcolor="rgba(0,0,0,0)",
              plot_bgcolor="rgba(0,0,0,0)"
            )

            # Update Axes
            fig_tel.update_yaxes(showgrid=True, gridcolor='#333')
            fig_tel.update_xaxes(showgrid=False, visible=False)  # Hide X on top plots
            fig_tel.update_xaxes(title_text="Total Distance (m)", visible=True, row=5, col=1)  # Show X only on bottom

            st.plotly_chart(fig_tel, use_container_width=True)

        # === TAB 2: OVERVIEW ===
        with tab_overview:
          st.subheader("🏁 Race Progression & Positions")

          # 1. Bar Chart: Grid vs Finish
          st.markdown("##### Position Changes: Start vs Finish")
          if not positions_df.empty:
            fig_pos = px.bar(
              positions_df,
              x="full_name",
              y="position",
              color="type",
              barmode="group",
              title="",
              text_auto=True,
              labels={"full_name": "Driver", "position": "Position", "type": "Status"}
            )
            st.plotly_chart(fig_pos, use_container_width=True)

          st.divider()

          # --- NEW: Leaderboard Table ---
          st.subheader("🏆 Championship Standings Impact")

          # Fetch the new tables via the simplified processor
          df_drivers_standings, df_const_standings = DataProcessor.get_championship_tables(session_key)

          # 1. Constructors Table
          if not df_const_standings.empty:
            st.markdown("### 🏎️ Constructors Championship")
            st.dataframe(
              df_const_standings,
              hide_index=True,
              use_container_width=True,
              column_config={
                "Points Added": st.column_config.NumberColumn(
                  "Added",
                  format="+%d",  # Shows +25, +18 etc.
                  help="Points scored in this race"
                )
              }
            )

          st.divider()

          # 2. Drivers Table
          if not df_drivers_standings.empty:
            st.markdown("### 🧑‍✈️ Drivers Championship")
            st.dataframe(
              df_drivers_standings,
              hide_index=True,
              use_container_width=True,
              column_config={
                "Points Added": st.column_config.NumberColumn(
                  "Added",
                  format="+%d"
                )
              }
            )

        # === TAB 3: HEAD-TO-HEAD COMPARISON ===
        with tab_compare:
          st.subheader("⚔️ Fastest Lap Comparison")
          comp_data = st.session_state.get('comp_data', {})

          # Prepare list of drivers to plot
          drivers_to_plot = []
          # Add main driver
          drivers_to_plot.append((selected_driver, race_df, '#1f77b4'))  # Blue

          # Add comparison drivers
          colors = ['#ff7f0e', '#2ca02c']  # Orange, Green
          for i, (name, df) in enumerate(comp_data.items()):
            color = colors[i % len(colors)]
            drivers_to_plot.append((name, df, color))

          if race_df is not None:
            # Create subplots structure
            fig_comp = make_subplots(
              rows=3, cols=1,
              shared_xaxes=True,
              vertical_spacing=0.08,
              row_heights=[0.5, 0.25, 0.25],
              subplot_titles=("Speed Comparison (km/h)", "Throttle (%)", "Brake (Y/N")
            )

            for name, df, color in drivers_to_plot:
              if df.empty: continue

              # 1. Safely retrieve driver number from the main drivers list
              # (Prevent KeyError by looking up via name in master list)
              current_driver_num = df_driver.loc[df_driver['full_name'] == name, 'driver_number'].iloc[0]

              # 2. Fetch official lap times
              laps_official, _ = F1_API.get_laps(session_key, current_driver_num)
              valid_laps = laps_official.dropna(subset=['lap_duration'])

              # Safe variable initialization
              fastest_lap_num = df['lap_number'].max()
              raw_time = "N/A"

              # 3. Find the fastest lap based on duration
              if not valid_laps.empty:
                fastest_idx = valid_laps['lap_duration'].idxmin()
                fastest_lap_num = valid_laps.loc[fastest_idx, 'lap_number']

                # Format time string
                t_str = str(valid_laps.loc[fastest_idx, 'lap_duration'])
                raw_time = t_str.split('days')[-1].strip()
                if '.' in raw_time and len(raw_time.split('.')[-1]) > 3:
                  raw_time = raw_time[:-3]

              # 4. Slice data for specific lap + Normalize X-Axis
              lap_data = df[df['lap_number'] == fastest_lap_num].copy()

              # Skip if no data exists for this specific lap
              if lap_data.empty:
                continue

              # --- Normalization: Create dist_norm column ---
              # Subtract the starting distance so all laps start at 0m for accurate comparison
              lap_data['dist_norm'] = lap_data['Total_distance'] - lap_data['Total_distance'].min()

              legend_label = f"{name} (Lap {int(fastest_lap_num)} | {raw_time})"

              # --- Trace 1: Speed ---
              fig_comp.add_trace(
                go.Scatter(
                  x=lap_data['dist_norm'], y=lap_data['speed'],
                  name=f"{legend_label}", legendgroup=name,
                  line=dict(color=color, width=2)
                ), row=1, col=1
              )

              # --- Trace 2: Throttle ---
              fig_comp.add_trace(
                go.Scatter(
                  x=lap_data['dist_norm'], y=lap_data['throttle'],
                  name=f"{name} Throttle", legendgroup=name, showlegend=False,
                  line=dict(color=color, width=1.5)
                ), row=2, col=1
              )

              # --- Trace 3: Brake ---
              fig_comp.add_trace(
                go.Scatter(
                  x=lap_data['dist_norm'], y=lap_data['brake'],
                  name=f"{name} Brake", legendgroup=name, showlegend=False,
                  line=dict(color=color, width=1.5)
                ), row=3, col=1
              )

            # Layout Polish for Comparison Chart
            fig_comp.update_layout(
              height=800,
              hovermode="x unified",
              margin=dict(l=0, r=0, t=40, b=0),
              paper_bgcolor="rgba(0,0,0,0)",
              plot_bgcolor="rgba(0,0,0,0)",
              legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center")
            )

            # Update X-axis (Apply to the bottom chart)
            fig_comp.update_xaxes(title_text="Lap Distance (m)", visible=True, row=3, col=1)
            fig_comp.update_xaxes(showgrid=False, visible=False, row=1, col=1)
            fig_comp.update_xaxes(showgrid=False, visible=False, row=2, col=1)

            # Final Render Command (Was missing in previous versions)
            st.plotly_chart(fig_comp, use_container_width=True)

else:
  # Initial State (Before clicking button)
  st.info("👈 Please select a session and click 'Load Data' to begin.")








