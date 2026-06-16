import streamlit as st
import pandas as pd
from database.db import get_all_violations, get_statistics
import config


def show():
    st.title("Violation Records")
    st.markdown("Search and review all detected traffic violations")

    stats = get_statistics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Violations", stats['total'])
    with col2:
        st.metric("No Helmet", stats['no_helmet'])
    with col3:
        st.metric("Triple Riding", stats['triple_riding'])
    with col4:
        st.metric("Unique Vehicles", stats['unique_vehicles'])

    st.divider()

    st.subheader("Search Filters")

    col1, col2, col3 = st.columns(3)
    with col1:
        search_vehicle = st.text_input("Search by Vehicle Number", placeholder="e.g., KA-01-AB-1234")
    with col2:
        violation_types = ['All'] + list(config.VIOLATION_TYPES.keys())
        search_type = st.selectbox("Filter by Violation Type", violation_types)
    with col3:
        search_date = st.date_input("Filter by Date", value=None)

    filter_type = None if search_type == 'All' else search_type
    date_from = search_date.isoformat() if search_date else None
    date_to = search_date.isoformat() + 'T23:59:59' if search_date else None

    violations = get_all_violations(
        vehicle_number=search_vehicle if search_vehicle else None,
        violation_type=filter_type,
        date_from=date_from,
        date_to=date_to,
    )

    st.subheader(f"Found {len(violations)} Record(s)")

    if violations:
        data = []
        for v in violations:
            data.append({
                'ID': v.id,
                'Vehicle Number': v.vehicle_number or '-',
                'Vehicle Type': v.vehicle_type.capitalize() if v.vehicle_type else '-',
                'Violation Type': config.VIOLATION_TYPES.get(v.violation_type, v.violation_type),
                'Confidence': f"{v.confidence:.1%}",
                'Timestamp': v.timestamp,
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="violation_records.csv",
            mime="text/csv",
        )

        st.subheader("Record Details")
        record_ids = [v.id for v in violations]
        selected_id = st.selectbox("Select a record to view details", record_ids)
        selected = next((v for v in violations if v.id == selected_id), None)
        if selected:
            st.json(selected.to_dict())
    else:
        st.info("No violations found matching your criteria.")


if __name__ == '__main__':
    show()
