import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db import (
    get_all_violations,
    get_statistics,
    get_top_repeat_offenders,
    get_violations_by_type,
    get_monthly_trend,
)
import config


VIOLATION_TYPE_MAP = {v: k for k, v in config.VIOLATION_TYPES.items()}
VIOLATION_TYPE_MAP.update({k.lower(): k for k in config.VIOLATION_TYPES})


def process_query(query):
    query_lower = query.lower().strip()

    if not query_lower:
        return "Please ask a question about traffic violations."

    if query_lower in ['hi', 'hello', 'hey']:
        stats = get_statistics()
        return (
            f"Hello! I am TRINETRA AI Copilot. I can help you analyze traffic violation data. "
            f"There are currently **{stats['total']}** violations recorded in the system. "
            f"Try asking me about helmet violations, repeat offenders, or violation statistics."
        )

    if 'help' in query_lower:
        return (
            "I can answer questions like:\n"
            "- Show helmet violations\n"
            "- Show triple riding cases\n"
            "- Show repeat offenders\n"
            "- Show top violating vehicles\n"
            "- Show violation statistics\n"
            "- Show violations today\n"
            "- Show monthly trend\n"
            "- Show records for vehicle [number]"
        )

    if 'helmet' in query_lower or 'no helmet' in query_lower:
        violations = get_all_violations(violation_type='NO_HELMET')
        stats = get_statistics()
        if 'today' in query_lower:
            today = datetime.now().strftime('%Y-%m-%d')
            today_violations = [v for v in violations if v.timestamp.startswith(today)]
            if today_violations:
                return f"There are **{len(today_violations)}** helmet violations recorded today."
            return f"No helmet violations recorded today. Total helmet violations: **{stats['no_helmet']}**."
        if violations:
            response = f"Found **{len(violations)}** helmet violations"
            if violations:
                sample = violations[:5]
                response += ". Recent examples:\n"
                for v in sample:
                    vnum = v.vehicle_number if v.vehicle_number else 'Unknown'
                    response += f"- {vnum} ({v.timestamp[:10]})\n"
            return response
        return "No helmet violations found in the database."

    if 'triple' in query_lower or 'triple riding' in query_lower or '3' in query_lower:
        violations = get_all_violations(violation_type='TRIPLE_RIDING')
        stats = get_statistics()
        if 'today' in query_lower:
            today = datetime.now().strftime('%Y-%m-%d')
            today_v = [v for v in violations if v.timestamp.startswith(today)]
            if today_v:
                return f"There are **{len(today_v)}** triple riding violations recorded today."
            return f"No triple riding violations today. Total: **{stats['triple_riding']}**."
        if violations:
            return f"Found **{len(violations)}** triple riding violations. Total cases: **{stats['triple_riding']}**."
        return "No triple riding violations found."

    if 'statistics' in query_lower or 'stats' in query_lower or 'summary' in query_lower:
        stats = get_statistics()
        by_type = get_violations_by_type()
        response = "## Violation Statistics\n\n"
        response += f"- **Total Violations:** {stats['total']}\n"
        response += f"- **No Helmet:** {stats['no_helmet']}\n"
        response += f"- **Triple Riding:** {stats['triple_riding']}\n"
        response += f"- **Unique Vehicles:** {stats['unique_vehicles']}\n\n"
        if by_type:
            response += "### Violations by Type\n"
            for item in by_type:
                vname = config.VIOLATION_TYPES.get(item['type'], item['type'])
                response += f"- {vname}: {item['count']}\n"
        return response

    if 'repeat offender' in query_lower or 'top' in query_lower or 'offender' in query_lower:
        offenders = get_top_repeat_offenders(limit=10)
        if offenders:
            filtered = [o for o in offenders if o['vehicle']]
            if filtered:
                response = "### Top Repeat Offenders\n\n"
                for i, o in enumerate(filtered[:5], 1):
                    response += f"{i}. **{o['vehicle']}** - {o['count']} violations ({o['types']})\n"
                return response
        return "No repeat offenders data available."

    if 'vehicle' in query_lower or 'number' in query_lower or 'plate' in query_lower:
        parts = query_lower.split()
        vehicle_number = None
        for p in parts:
            cleaned = ''.join(c for c in p if c.isalnum() or c in '- ')
            if len(cleaned) >= 4:
                vehicle_number = cleaned
                break
        if vehicle_number:
            violations = get_all_violations(vehicle_number=vehicle_number)
            if violations:
                response = f"### Records for {vehicle_number.upper()}\n\n"
                response += f"Found **{len(violations)}** violation(s):\n\n"
                for v in violations:
                    vname = config.VIOLATION_TYPES.get(v.violation_type, v.violation_type)
                    response += f"- {vname} on {v.timestamp[:10]} (Confidence: {v.confidence:.0%})\n"
                return response
            return f"No violations found for vehicle **{vehicle_number.upper()}**."

        violations = get_all_violations()
        vehicles = set(v.vehicle_number for v in violations if v.vehicle_number)
        if vehicles:
            response = f"### Vehicles with Violations ({len(vehicles)} total)\n\n"
            for v in sorted(list(vehicles))[:10]:
                count = sum(1 for x in violations if x.vehicle_number == v)
                response += f"- {v}: {count} violation(s)\n"
            return response
        return "No vehicle data available."

    if 'highest' in query_lower or 'top confidence' in query_lower or 'most confident' in query_lower:
        violations = get_all_violations()
        if violations:
            sorted_v = sorted(violations, key=lambda v: v.confidence, reverse=True)[:5]
            response = "### Highest Confidence Violations\n\n"
            for i, v in enumerate(sorted_v, 1):
                vname = config.VIOLATION_TYPES.get(v.violation_type, v.violation_type)
                vnum = v.vehicle_number if v.vehicle_number else 'Unknown'
                response += f"{i}. **{vname}** - {vnum} ({v.confidence:.0%} confidence)\n"
            return response
        return "No violations in the database."

    if 'monthly' in query_lower or 'trend' in query_lower:
        trend = get_monthly_trend(months=6)
        if trend:
            response = "### Monthly Violation Trend\n\n"
            for t in trend:
                response += f"- {t['month']}: {t['count']} violations\n"
            return response
        return "No monthly trend data available."

    if 'today' in query_lower:
        today = datetime.now().strftime('%Y-%m-%d')
        violations = get_all_violations(date_from=today, date_to=today + 'T23:59:59')
        if violations:
            response = f"### Violations Today ({today})\n\n"
            response += f"Total: **{len(violations)}** violation(s)\n\n"
            for v in violations:
                vname = config.VIOLATION_TYPES.get(v.violation_type, v.violation_type)
                response += f"- {vname} - {v.vehicle_number or 'Unknown'} ({v.timestamp[11:19]})\n"
            return response
        return f"No violations recorded today ({today})."

    return (
        "I'm not sure how to answer that. Here are some things you can ask:\n"
        "- Show helmet violations\n"
        "- Show violation statistics\n"
        "- Show repeat offenders\n"
        "- Show records for vehicle [number]\n"
        "- Show monthly trend\n"
        "- Type 'help' for more options"
    )


def show():
    st.title("AI Copilot")
    st.markdown("Ask questions about traffic violations in natural language")

    st.markdown("""
    <style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .user-message {
        background-color: #262730;
        border-left: 3px solid #ff4444;
    }
    .bot-message {
        background-color: #1e1e1e;
        border-left: 3px solid #00ff88;
    }
    </style>
    """, unsafe_allow_html=True)

    if 'copilot_messages' not in st.session_state:
        st.session_state.copilot_messages = []
        st.session_state.copilot_messages.append({
            'role': 'assistant',
            'content': "Hello! I am TRINETRA AI Copilot. Ask me about traffic violations in the database."
        })

    for msg in st.session_state.copilot_messages:
        role_class = "user-message" if msg['role'] == 'user' else "bot-message"
        icon = "👤" if msg['role'] == 'user' else "🤖"
        st.markdown(
            f'<div class="chat-message {role_class}">'
            f'<strong>{icon} {msg["role"].title()}:</strong><br>'
            f'{msg["content"]}</div>',
            unsafe_allow_html=True
        )

    query = st.chat_input("Ask about traffic violations...")
    if query:
        st.session_state.copilot_messages.append({
            'role': 'user', 'content': query
        })
        with st.spinner("Thinking..."):
            response = process_query(query)
        st.session_state.copilot_messages.append({
            'role': 'assistant', 'content': response
        })
        st.rerun()

    if st.button("Clear Chat"):
        st.session_state.copilot_messages = []
        st.rerun()


if __name__ == '__main__':
    show()
