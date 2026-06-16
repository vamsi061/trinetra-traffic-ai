import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
from database.db import (
    get_violations_by_type,
    get_violations_by_day,
    get_top_repeat_offenders,
    get_monthly_trend,
    get_statistics,
)
import config

pio.templates.default = "plotly_dark"


def show():
    st.title("Violation Analytics")
    st.markdown("Visual analytics and insights from traffic violation data")

    stats = get_statistics()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Violations", stats['total'])
    with col2:
        st.metric("No Helmet Cases", stats['no_helmet'])
    with col3:
        st.metric("Triple Riding Cases", stats['triple_riding'])

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Violations by Type", "Daily Trend",
        "Repeat Offenders", "Monthly Trend"
    ])

    with tab1:
        st.subheader("Violations by Type")
        data = get_violations_by_type()
        if data:
            df = pd.DataFrame(data)
            df['type'] = df['type'].map(lambda t: config.VIOLATION_TYPES.get(t, t))
            fig = px.pie(
                df, values='count', names='type',
                title='Distribution of Violation Types',
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            fig.update_traces(textposition='inside', textinfo='percent+label',
                              textfont_color='#ffffff')
            st.plotly_chart(fig, use_container_width=True)

            fig2 = px.bar(
                df, x='type', y='count',
                title='Violations by Type (Bar Chart)',
                color='type',
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No violation data available yet.")

    with tab2:
        st.subheader("Violations by Day (Last 30 Days)")
        data = get_violations_by_day(days=30)
        if data:
            df = pd.DataFrame(data)
            df['day'] = pd.to_datetime(df['day'])
            fig = px.line(
                df, x='day', y='count',
                title='Daily Violation Trend',
                markers=True,
                line_shape='linear',
                color_discrete_sequence=['#ff6b6b'],
            )
            fig.update_traces(marker=dict(size=8, color='#ff6b6b'))
            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Number of Violations',
            )
            st.plotly_chart(fig, use_container_width=True)

            fig2 = px.area(
                df, x='day', y='count',
                title='Daily Violation Volume',
                color_discrete_sequence=['#ff6b6b'],
            )
            fig2.update_traces(fillcolor='rgba(255, 107, 107, 0.5)', line_color='#ff6b6b')
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No daily trend data available yet.")

    with tab3:
        st.subheader("Top Repeat Offenders")
        data = get_top_repeat_offenders(limit=10)
        if data:
            df = pd.DataFrame(data)
            df = df[df['vehicle'] != '']
            if not df.empty:
                fig = px.bar(
                    df, x='vehicle', y='count',
                    title='Top Repeat Offenders',
                    color='count',
                    color_continuous_scale='Reds',
                    text='count',
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(
                    xaxis_title='Vehicle Number',
                    yaxis_title='Violation Count',
                    xaxis_tickangle=-45,
                )
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Offender Details")
                for _, row in df.iterrows():
                    with st.expander(f"{row['vehicle']} - {row['count']} violations"):
                        st.write(f"**Vehicle:** {row['vehicle']}")
                        st.write(f"**Total Violations:** {row['count']}")
                        st.write(f"**Violation Types:** {row['types']}")
            else:
                st.info("No repeat offenders data available.")
        else:
            st.info("No repeat offenders data available yet.")

    with tab4:
        st.subheader("Monthly Trend (Last 6 Months)")
        data = get_monthly_trend(months=6)
        if data:
            df = pd.DataFrame(data)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df['month'],
                y=df['count'],
                name='Violations',
                marker_color='#ff6b6b',
            ))
            fig.add_trace(go.Scatter(
                x=df['month'],
                y=df['count'],
                name='Trend',
                mode='lines+markers',
                line=dict(color='#c0392b', width=3),
                marker=dict(size=8),
            ))
            fig.update_layout(
                title='Monthly Violation Trend',
                xaxis_title='Month',
                yaxis_title='Number of Violations',
                hovermode='x unified',
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No monthly trend data available yet.")


if __name__ == '__main__':
    show()
