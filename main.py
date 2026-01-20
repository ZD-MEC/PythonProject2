import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st

df = sns.load_dataset('penguins')

st.title('My first app')

plot_choice = st.radio('Choose you plot library:', ['Seaborn', 'Plotly'])

if plot_choice == 'Seaborn':
  fig, ax = plt.subplots()
  sns.scatterplot(data=df, x='flipper_length_mm', y='body_mass_g', hue='species')
  st.pyplot(fig)

elif plot_choice == 'Plotly':
  fig = px.scatter(df, x= 'flipper_length_mm', y='body_mass_g', color='species', title = 'Pegnguins')
  st.plotly_chart(fig)