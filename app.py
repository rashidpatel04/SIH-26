# ============================================================
# MINDSETU NER - COMPLETE VOICE-FIRST STREAMLIT APP
# ============================================================
#
# FEATURES
#
# 1. Patient / Doctor / Admin roles
# 2. Patient registration and login
# 3. Admin dashboard
# 4. Admin can add doctors
# 5. Admin can assign patients to doctors
# 6. Doctor can see assigned patients only
# 7. Doctor cannot access games
# 8. Patient cognitive games
# 9. Memory Sequence Game
# 10. Pattern Memory Game
# 11. Attention Game
# 12. Adaptive difficulty
# 13. Difficulty increases after strong performance
# 14. Difficulty decreases after weak performance
# 15. Personal history
# 16. Personal baseline
# 17. Reminders
# 18. Doctor reports
# 19. Patient can listen to reports
# 20. Hidden voice output
# 21. Voice welcome after login
# 22. Voice confirmation after actions
# 23. Voice commands
# 24. Multilingual voice output
# 25. Multilingual voice recognition
# 26. Multilingual UI
# 27. Game Exit Option
# 28. 15-20 Round Cognitive Games
# 29. Last 5 Games Progress Graph
# 30. North-East Regional Language Options
# 31. Doctor Registration + Qualification Verification
# 32. Caretaker Registration
# 33. Phone / Email / Location for providers and patients
# 34. Provider-driven Add Patient onboarding
# 35. Automatic patient -> doctor/caretaker linking
# 36. Provider-owned patient privacy
# 37. Admin management / verification instead of central patient assignment
# 38. 10-second Memory Sequence viewing period
# 39. Memory sequence hides automatically before answer entry
# 40. Congratulations message after strong game completion
# 41. Visible adaptive difficulty increase notification
# 42. Image Recognition / Image Memory Game
# 43. 10-second image viewing countdown
# 44. Image answers activate only after countdown reaches 0
# 45. Image game results saved to performance history
#
# INSTALL:
#
# pip install streamlit gTTS SpeechRecognition streamlit-mic-recorder reportlab pandas streamlit-autorefresh
#
# RUN:
#
# streamlit run app.py
#
# ============================================================

import streamlit as st
import sqlite3
import random
import hashlib
import io
import re
import base64
import textwrap
import pandas as pd

from datetime import datetime, date, time
from uuid import uuid4
import time as pytime

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
        KeepTogether,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ============================================================
# OPTIONAL PACKAGES
# ============================================================

try:
    from gtts import gTTS
except ImportError:
    gTTS = None


try:
    import speech_recognition as sr
except ImportError:
    sr = None


try:
    from streamlit_mic_recorder import mic_recorder
except ImportError:
    mic_recorder = None


# Reliable one-second browser-driven reruns for countdown games.
# This is used instead of time.sleep(), which would block Streamlit UI updates.
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MINDSETU NER",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)



# ============================================================
# CLINICAL-STYLE PROGRESS REPORT PDF
# ============================================================

REPORT_GREEN = colors.HexColor("#005B4F") if REPORTLAB_AVAILABLE else None
REPORT_DARK = colors.HexColor("#253047") if REPORTLAB_AVAILABLE else None
REPORT_LIGHT = colors.HexColor("#F4F7FA") if REPORTLAB_AVAILABLE else None
REPORT_BORDER = colors.HexColor("#D9E2EC") if REPORTLAB_AVAILABLE else None
REPORT_TEAL = colors.HexColor("#00A67A") if REPORTLAB_AVAILABLE else None


def safe_pdf_text(value):
    """Keep generated PDFs readable and avoid accidental unsupported glyphs."""
    if value is None:
        return "Not provided"
    return str(value).replace("–", "-").replace("—", "-")


def generate_automatic_doctor_observation(
    patient_name,
    sessions,
    current_difficulty,
    baseline,
    doctor_name=None,
):
    """
    Generate a neutral, data-driven observation automatically from the
    patient's recorded app performance. This is NOT a medical diagnosis
    and is not presented as a real doctor's authored note.
    """
    scores = [float(row[1]) for row in sessions]
    total = len(scores)
    average = sum(scores) / total if total else 0.0
    best = max(scores) if scores else 0.0
    lowest = min(scores) if scores else 0.0

    if total == 0:
        return (
            f"Patient {patient_name} has no recorded cognitive game sessions yet. "
            "There is insufficient performance data to generate an observation. "
            "Begin regular cognitive sessions to establish a longitudinal baseline."
        )

    strong = sum(1 for s in scores if s >= 70)
    weak = sum(1 for s in scores if s < 70)

    # Trend from first half to second half of sessions.
    midpoint = max(1, total // 2)
    early_avg = sum(scores[:midpoint]) / len(scores[:midpoint])
    late_avg = sum(scores[midpoint:]) / len(scores[midpoint:]) if total > midpoint else early_avg
    trend_change = late_avg - early_avg

    parts = []
    parts.append(
        f"Automated performance observation for {patient_name}: "
        f"{total} cognitive session(s) recorded with an average score of "
        f"{average:.1f}/100 and a best score of {best:.0f}/100."
    )

    if average >= 80:
        parts.append(
            "Overall performance is strong across the recorded sessions. "
            "The patient is demonstrating consistent task completion at the current level."
        )
    elif average >= 60:
        parts.append(
            "Overall performance is moderate. The patient is completing tasks with "
            "variable performance and may benefit from continued structured practice."
        )
    else:
        parts.append(
            "Overall performance is below the application's strong-performance threshold. "
            "Continued guided practice may help establish a more stable performance pattern."
        )

    if trend_change >= 10:
        parts.append(
            f"Recent session performance is improving by approximately {trend_change:.1f} points "
            "compared with the earlier recorded sessions."
        )
    elif trend_change <= -10:
        parts.append(
            f"Recent session performance is lower by approximately {abs(trend_change):.1f} points "
            "compared with the earlier recorded sessions."
        )
    else:
        parts.append(
            "Recent performance is relatively stable compared with the earlier recorded sessions."
        )

    parts.append(
        f"Strong-performance sessions: {strong}; lower-performance sessions: {weak}. "
        f"Current adaptive difficulty: level {int(current_difficulty or 1)}."
    )

    if baseline and float(baseline) > 0:
        parts.append(
            f"Recorded personal baseline: {float(baseline):.1f}/100."
        )

    parts.append(
        "This observation is generated automatically from application records and "
        "should not be treated as a medical diagnosis or a substitute for evaluation "
        "by a qualified clinician."
    )

    return " ".join(parts)


def build_patient_progress_pdf(patient_id):
    """
    Build a clinical-report-inspired PDF using only data available in the app.
    This intentionally does NOT claim medical verification, diagnosis, ISO, or HL7 compliance.
    Returns PDF bytes, or None when ReportLab is unavailable.
    """
    if not REPORTLAB_AVAILABLE:
        return None

    patient = conn.execute(
        """
        SELECT
            id,
            name,
            username,
            language,
            baseline,
            role,
            doctor_id,
            adaptive_difficulty
        FROM users
        WHERE id=?
        AND role='patient'
        """,
        (patient_id,)
    ).fetchone()

    if not patient:
        return None

    sessions = conn.execute(
        """
        SELECT
            game,
            score,
            difficulty,
            created_at
        FROM sessions
        WHERE user_id=?
        ORDER BY id ASC
        """,
        (patient_id,)
    ).fetchall()

    reminders = conn.execute(
        """
        SELECT
            title,
            due_time,
            status
        FROM reminders
        WHERE user_id=?
        ORDER BY due_time ASC
        LIMIT 12
        """,
        (patient_id,)
    ).fetchall()

    doctor_name = "Not assigned"
    if patient[6]:
        doctor = conn.execute(
            """
            SELECT name
            FROM users
            WHERE id=?
            AND role='doctor'
            """,
            (patient[6],)
        ).fetchone()
        if doctor:
            doctor_name = f"Dr. {doctor[0]}"

    # Get the latest actual doctor report, when one exists.
    latest_doctor_report = conn.execute(
        """
        SELECT
            r.title,
            r.report_text,
            r.created_at,
            d.name
        FROM reports r
        INNER JOIN users d
        ON r.doctor_id=d.id
        WHERE r.patient_id=?
        AND d.role='doctor'
        ORDER BY r.id DESC
        LIMIT 1
        """,
        (patient_id,)
    ).fetchone()

    total_sessions = len(sessions)
    scores = [float(row[1]) for row in sessions]
    mean_accuracy = round(sum(scores) / len(scores), 1) if scores else 0.0
    best_score = max(scores) if scores else 0.0
    mean_latency = "Not available"

    # Automatically generate a data-driven observation for every report.
    auto_observation = generate_automatic_doctor_observation(
        patient_name=patient[1],
        sessions=sessions,
        current_difficulty=patient[7] or 1,
        baseline=patient[4] or 0,
        doctor_name=(
            f"Dr. {latest_doctor_report[3]}"
            if latest_doctor_report else doctor_name
        ),
    )

    # If a real doctor report exists, retain it as an additional note rather
    # than requiring manual entry for the automatic observation.
    doctor_observation = {
        "title": "Automatically Generated Performance Observation",
        "text": auto_observation,
        "date": datetime.now().strftime("%d %b %Y %H:%M"),
        "doctor": (
            f"Dr. {latest_doctor_report[3]}"
            if latest_doctor_report
            else "System-generated"
        ),
        "is_automatic": True,
        "source_report": (
            {
                "title": safe_pdf_text(latest_doctor_report[0]),
                "text": safe_pdf_text(latest_doctor_report[1]),
                "date": safe_pdf_text(latest_doctor_report[2]),
                "doctor": f"Dr. {safe_pdf_text(latest_doctor_report[3])}",
            }
            if latest_doctor_report else None
        ),
    }

    # Group sessions into a compact cognitive-assessment table.
    grouped = {}
    for game, score, diff, created_at in sessions:
        key = safe_pdf_text(game)
        item = grouped.setdefault(
            key,
            {"count": 0, "scores": [], "difficulty": [], "dates": []}
        )
        item["count"] += 1
        item["scores"].append(float(score))
        item["difficulty"].append(int(diff or 1))
        item["dates"].append(created_at)

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="MINDSETU NER Cognitive Progress Report",
        author="MINDSETU NER",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.white,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name="Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=REPORT_DARK,
        spaceBefore=7,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#5C6670"),
    ))
    styles.add(ParagraphStyle(
        name="BodySmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#4D5560"),
    ))
    styles.add(ParagraphStyle(
        name="MetricLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#61708A"),
    ))
    styles.add(ParagraphStyle(
        name="MetricValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=16,
        textColor=REPORT_GREEN,
    ))
    styles.add(ParagraphStyle(
        name="MetricSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6,
        leading=7,
        textColor=colors.HexColor("#718096"),
    ))

    story = []

    # Header matching the reference report's visual hierarchy.
    header_table = Table([
        [
            [
                Paragraph("MINDSETU NER COGNITIVE HEALTH PLATFORM", styles["ReportTitle"]),
                Paragraph("Cognitive wellness and longitudinal performance report", styles["ReportSubtitle"]),
                Paragraph("Clinical-style summary generated from application data", styles["ReportSubtitle"]),
            ],
            [
                Paragraph("<b>APPLICATION REPORT</b><br/><font size='7'>Not a medical diagnosis or verified medical record</font>", styles["BodySmall"])
            ]
        ]],
        colWidths=[150 * mm, 0],
    )

    # Use a simpler two-column header to avoid unsupported nested widths.
    header_table = Table([
        [
            [
                Paragraph("MINDSETU NER COGNITIVE HEALTH PLATFORM", styles["ReportTitle"]),
                Paragraph("Cognitive wellness and longitudinal performance report", styles["ReportSubtitle"]),
                Paragraph("Clinical-style summary generated from application data", styles["ReportSubtitle"]),
            ],
            Paragraph("<b>APPLICATION REPORT</b><br/><font size='7'>Not a medical diagnosis</font>", styles["BodySmall"]),
        ]
    ], colWidths=[135 * mm, 40 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), REPORT_GREEN),
        ("BOX", (0, 0), (-1, -1), 0, REPORT_GREEN),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TEXTCOLOR", (1, 0), (1, 0), colors.white),
        ("BACKGROUND", (1, 0), (1, 0), colors.white),
        ("BOX", (1, 0), (1, 0), 0.6, colors.white),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 7 * mm))

    report_id = f"MNE-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6].upper()}"
    generated_at = datetime.now().strftime("%d %b %Y %H:%M:%S")

    meta_table = Table([
        [
            Paragraph("<b>COGNITIVE PROGRESS SUMMARY</b>", styles["BodySmall"]),
        ],
        [
            Paragraph(
                f"Report ID: {safe_pdf_text(report_id)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Generated: {safe_pdf_text(generated_at)} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"App User: {safe_pdf_text(patient[2])}",
                styles["Small"]
            )
        ]
    ], colWidths=[175 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.6, REPORT_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)

    def section_title(number, title):
        table = Table([["", Paragraph(f"{number}. {title}", styles["Section"])]], colWidths=[5 * mm, 170 * mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), REPORT_TEAL),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return table

    # Section 1 - Profile.
    story.append(section_title(1, "PATIENT PROFILE & APPLICATION DETAILS"))
    profile_data = [
        [Paragraph("<b>Patient Name:</b>", styles["BodySmall"]), safe_pdf_text(patient[1]), Paragraph("<b>Username:</b>", styles["BodySmall"]), safe_pdf_text(patient[2])],
        [Paragraph("<b>Role:</b>", styles["BodySmall"]), safe_pdf_text(patient[5].title()), Paragraph("<b>Language:</b>", styles["BodySmall"]), safe_pdf_text(patient[3])],
        [Paragraph("<b>Personal Baseline:</b>", styles["BodySmall"]), f"{float(patient[4] or 0):.1f}", Paragraph("<b>Adaptive Difficulty:</b>", styles["BodySmall"]), str(int(patient[7] or 1))],
        [Paragraph("<b>Assigned Provider:</b>", styles["BodySmall"]), safe_pdf_text(doctor_name), Paragraph("<b>Clinical Fields:</b>", styles["BodySmall"]), "Provider-managed onboarding"],
    ]
    profile_table = Table(profile_data, colWidths=[36 * mm, 52 * mm, 38 * mm, 49 * mm])
    profile_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F8FA")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F5F8FA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (1, 0), (-1, -1), 7.5),
        ("TEXTCOLOR", (1, 0), (-1, -1), colors.HexColor("#4D5560")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 5 * mm))

    # Section 2 - Metrics.
    story.append(section_title(2, "LONGITUDINAL COGNITIVE METRICS & PERFORMANCE INDICES"))
    metric_values = [
        ("TOTAL SESSIONS", str(total_sessions), "Evaluated runs"),
        ("MEAN SCORE", f"{mean_accuracy:.0f}%", "Average game score"),
        ("BEST SCORE", f"{best_score:.0f}", "Highest recorded score"),
        ("ADAPTIVE LEVEL", str(int(patient[7] or 1)), "Current difficulty"),
    ]
    metric_cells = []
    for label, value, sub in metric_values:
        metric_cells.append([
            Paragraph(label, styles["MetricLabel"]),
            Paragraph(value, styles["MetricValue"]),
            Paragraph(sub, styles["MetricSub"]),
        ])
    metric_table = Table([metric_cells], colWidths=[43.5 * mm] * 4)
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 3 * mm))

    assessment_rows = [[
        Paragraph("<b>Cognitive Assessment</b>", styles["BodySmall"]),
        Paragraph("<b>Sessions</b>", styles["BodySmall"]),
        Paragraph("<b>Mean Score</b>", styles["BodySmall"]),
        Paragraph("<b>Difficulty</b>", styles["BodySmall"]),
        Paragraph("<b>Application Interpretation</b>", styles["BodySmall"]),
    ]]
    for game, info in grouped.items():
        avg = sum(info["scores"]) / len(info["scores"])
        avg_diff = round(sum(info["difficulty"]) / len(info["difficulty"]))
        interpretation = (
            "Strong performance recorded."
            if avg >= 70 else
            "Performance may benefit from continued practice."
        )
        assessment_rows.append([
            Paragraph(safe_pdf_text(game), styles["BodySmall"]),
            str(info["count"]),
            f"{avg:.0f}%",
            str(avg_diff),
            Paragraph(interpretation, styles["BodySmall"]),
        ])

    if len(assessment_rows) == 1:
        assessment_rows.append([
            "No sessions recorded", "0", "0%", str(int(patient[7] or 1)),
            Paragraph("No cognitive sessions are available yet.", styles["BodySmall"])
        ])

    assessment_table = Table(
        assessment_rows,
        colWidths=[54 * mm, 20 * mm, 25 * mm, 25 * mm, 51 * mm],
        repeatRows=1,
    )
    assessment_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), REPORT_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (3, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(assessment_table)

    # Section 3 - reminders/care schedule. We use reminders rather than claiming medications.
    story.append(Spacer(1, 5 * mm))
    story.append(section_title(3, "REMINDER & CARE SCHEDULE"))
    reminder_rows = [[
        Paragraph("<b>Time</b>", styles["BodySmall"]),
        Paragraph("<b>Reminder</b>", styles["BodySmall"]),
        Paragraph("<b>Status</b>", styles["BodySmall"]),
    ]]
    for title, due_time, status in reminders:
        reminder_rows.append([
            safe_pdf_text(due_time),
            Paragraph(safe_pdf_text(title), styles["BodySmall"]),
            safe_pdf_text(status),
        ])
    if len(reminder_rows) == 1:
        reminder_rows.append([
            "-",
            Paragraph("No reminders scheduled.", styles["BodySmall"]),
            "-",
        ])
    reminder_table = Table(reminder_rows, colWidths=[32 * mm, 92 * mm, 51 * mm], repeatRows=1)
    reminder_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), REPORT_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(reminder_table)

    story.append(PageBreak())

    # Section 4 - full session audit.
    story.append(section_title(4, "GAME-BY-GAME SESSION AUDIT LOG"))
    audit_rows = [[
        Paragraph("#", styles["BodySmall"]),
        Paragraph("Date & Time", styles["BodySmall"]),
        Paragraph("Cognitive Assessment", styles["BodySmall"]),
        Paragraph("Difficulty", styles["BodySmall"]),
        Paragraph("Score", styles["BodySmall"]),
        Paragraph("Status", styles["BodySmall"]),
    ]]
    for idx, (game, score, diff, created_at) in enumerate(sessions, start=1):
        status = "Optimal" if float(score) >= 70 else "Attention"
        audit_rows.append([
            str(idx),
            safe_pdf_text(created_at),
            Paragraph(safe_pdf_text(game), styles["BodySmall"]),
            str(int(diff or 1)),
            f"{float(score):.0f}/100",
            status,
        ])
    if len(audit_rows) == 1:
        audit_rows.append(["-", "-", "No sessions recorded", "-", "-", "-"])

    audit_table = Table(
        audit_rows,
        colWidths=[9 * mm, 34 * mm, 62 * mm, 21 * mm, 23 * mm, 26 * mm],
        repeatRows=1,
    )
    audit_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), REPORT_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (5, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(audit_table)

    # Section 5 - automatically generated observation.
    story.append(Spacer(1, 5 * mm))
    story.append(section_title(5, "DOCTOR OBSERVATION"))

    observation_header = Table([
        [
            Paragraph("<b>Source</b>", styles["BodySmall"]),
            Paragraph("Automatically generated from recorded app performance", styles["BodySmall"]),
            Paragraph("Date", styles["BodySmall"]),
            Paragraph(safe_pdf_text(doctor_observation["date"]), styles["BodySmall"]),
        ],
        [
            Paragraph("<b>Status</b>", styles["BodySmall"]),
            Paragraph("Auto-generated", styles["BodySmall"]),
            Paragraph("Doctor", styles["BodySmall"]),
            Paragraph(safe_pdf_text(doctor_observation["doctor"]), styles["BodySmall"]),
        ],
    ], colWidths=[28 * mm, 70 * mm, 25 * mm, 52 * mm])
    observation_header.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F5F8FA")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F5F8FA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(observation_header)
    story.append(Spacer(1, 3 * mm))

    observation_box = Table([
        [Paragraph(
            safe_pdf_text(doctor_observation["text"]).replace("\n", "<br/>") ,
            styles["BodySmall"]
        )]
    ], colWidths=[175 * mm])
    observation_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.6, REPORT_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(observation_box)

    # Show the real doctor's latest report automatically when it exists.
    if latest_doctor_report:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            "<b>Latest Doctor-Submitted Note</b>",
            styles["BodySmall"]
        ))
        submitted_note = Table([[Paragraph(
            safe_pdf_text(latest_doctor_report[1]).replace("\n", "<br/>") ,
            styles["BodySmall"]
        )]], colWidths=[175 * mm])
        submitted_note.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF9E8")),
            ("BOX", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(submitted_note)

    story.append(Spacer(1, 5 * mm))
    story.append(section_title(6, "PERFORMANCE SUMMARY & APP GUIDANCE"))

    if total_sessions:
        guidance = (
            f"The application recorded {total_sessions} cognitive session(s) with a mean score of "
            f"{mean_accuracy:.1f}/100 and a best score of {best_score:.0f}/100. "
            f"The current adaptive difficulty is level {int(patient[7] or 1)}. "
            "Continue structured cognitive practice and use reminders as configured in the app."
        )
    else:
        guidance = (
            "No cognitive sessions have been recorded yet. Start a cognitive game to begin "
            "building the longitudinal performance history."
        )

    guidance_table = Table([
        [Paragraph(guidance, styles["BodySmall"])]
    ], colWidths=[175 * mm])
    guidance_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, REPORT_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(guidance_table)

    story.append(Spacer(1, 7 * mm))
    footer_table = Table([
        [
            Paragraph("MINDSETU NER", styles["BodySmall"]),
            Paragraph(
                "Generated from application data. For demonstration and educational purposes only. "
                "This report does not provide a medical diagnosis.",
                styles["Small"]
            ),
        ]
    ], colWidths=[40 * mm, 135 * mm])
    footer_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, REPORT_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(footer_table)

    def draw_page(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(colors.HexColor("#718096"))
        canvas.drawString(16 * mm, 8 * mm, "MINDSETU NER | Cognitive Progress Report")
        canvas.drawRightString(194 * mm, 8 * mm, f"Page {doc_obj.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    buffer.seek(0)
    return buffer.getvalue()

# ============================================================
# DATABASE
# ============================================================

DB_NAME = "mindsetu_ner.db"


def get_connection():

    connection = sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )

    connection.execute("PRAGMA foreign_keys = ON")

    # --------------------------------------------------------
    # KEEP ORIGINAL USERS TABLE + ADD PROVIDER ONBOARDING FIELDS
    # --------------------------------------------------------
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            language TEXT DEFAULT 'English',
            baseline REAL DEFAULT 0,
            role TEXT DEFAULT 'patient',
            doctor_id INTEGER,
            adaptive_difficulty INTEGER DEFAULT 1,
            caretaker_id INTEGER,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            location TEXT DEFAULT '',
            qualification TEXT DEFAULT '',
            qualification_number TEXT DEFAULT '',
            qualification_document TEXT DEFAULT '',
            qualification_status TEXT DEFAULT 'Not Required',
            account_status TEXT DEFAULT 'Active',
            created_by_id INTEGER,
            created_at TEXT DEFAULT ''
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game TEXT NOT NULL,
            score REAL NOT NULL,
            difficulty INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            due_time TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            report_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'Sent'
        )
    """)

    # --------------------------------------------------------
    # SAFE MIGRATION FOR EXISTING DATABASES
    # --------------------------------------------------------
    existing_columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    }

    required_columns = {
        "adaptive_difficulty": "INTEGER DEFAULT 1",
        "caretaker_id": "INTEGER",
        "phone": "TEXT DEFAULT ''",
        "email": "TEXT DEFAULT ''",
        "location": "TEXT DEFAULT ''",
        "qualification": "TEXT DEFAULT ''",
        "qualification_number": "TEXT DEFAULT ''",
        "qualification_document": "TEXT DEFAULT ''",
        "qualification_status": "TEXT DEFAULT 'Not Required'",
        "account_status": "TEXT DEFAULT 'Active'",
        "created_by_id": "INTEGER",
        "created_at": "TEXT DEFAULT ''",
    }

    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}"
            )

    # Older patient accounts should remain usable.
    connection.execute("""
        UPDATE users
        SET account_status='Active'
        WHERE account_status IS NULL OR TRIM(account_status)=''
    """)

    connection.execute("""
        UPDATE users
        SET qualification_status='Not Required'
        WHERE qualification_status IS NULL OR TRIM(qualification_status)=''
    """)

    connection.execute("""
        UPDATE users
        SET created_at=datetime('now')
        WHERE created_at IS NULL OR TRIM(created_at)=''
    """)

    connection.commit()

    return connection


conn = get_connection()


# ============================================================
# PROVIDER / PATIENT SECURITY HELPERS
# ============================================================

def email_is_valid(email):
    if not email:
        return False
    return re.match(
        r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
        email.strip()
    ) is not None


def phone_is_valid(phone):
    if not phone:
        return False
    digits = re.sub(r"\D", "", phone)
    return 10 <= len(digits) <= 15


def normalize_location(location):
    return " ".join((location or "").strip().split())


def provider_can_manage_patient(provider_id, provider_role, patient_id):
    """Server-side ownership check for patient privacy."""
    if provider_role == "doctor":
        row = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id=?
            AND role='patient'
            AND doctor_id=?
            """,
            (patient_id, provider_id)
        ).fetchone()
        return row is not None

    if provider_role == "caretaker":
        row = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id=?
            AND role='patient'
            AND caretaker_id=?
            """,
            (patient_id, provider_id)
        ).fetchone()
        return row is not None

    return False


def provider_display_name(provider_row):
    if not provider_row:
        return "Not assigned"
    role = provider_row[1]
    prefix = "Dr. " if role == "doctor" else "Caretaker: "
    return prefix + provider_row[0]

# ============================================================
# LANGUAGE SETTINGS
# ============================================================

LANGUAGES = {

    "English": {
        "code": "en",
        "speech": "en-IN"
    },

    "Hindi": {
        "code": "hi",
        "speech": "hi-IN"
    },

    "Marathi": {
        "code": "mr",
        "speech": "mr-IN"
    },

    "Bengali": {
        "code": "bn",
        "speech": "bn-IN"
    },

    "Gujarati": {
        "code": "gu",
        "speech": "gu-IN"
    },

    "Tamil": {
        "code": "ta",
        "speech": "ta-IN"
    },

    "Telugu": {
        "code": "te",
        "speech": "te-IN"
    },

    "Kannada": {
        "code": "kn",
        "speech": "kn-IN"
    },

    "Malayalam": {
        "code": "ml",
        "speech": "ml-IN"
    },

    "Punjabi": {
        "code": "pa",
        "speech": "pa-IN"
    },

    "Urdu": {
        "code": "ur",
        "speech": "ur-PK"
    },

    "Nepali": {
        "code": "ne",
        "speech": "ne-NP"
    },

    "French": {
        "code": "fr",
        "speech": "fr-FR"
    },

    "Spanish": {
        "code": "es",
        "speech": "es-ES"
    },

    "German": {
        "code": "de",
        "speech": "de-DE"
    },

    "Italian": {
        "code": "it",
        "speech": "it-IT"
    },

    "Portuguese": {
        "code": "pt",
        "speech": "pt-PT"
    },

    "Arabic": {
        "code": "ar",
        "speech": "ar-SA"
    },

    "Chinese": {
        "code": "zh-CN",
        "speech": "zh-CN"
    },

    "Japanese": {
        "code": "ja",
        "speech": "ja-JP"
    },

    "Korean": {
        "code": "ko",
        "speech": "ko-KR"
    },

    "Russian": {
        "code": "ru",
        "speech": "ru-RU"
    },

    "Turkish": {
        "code": "tr",
        "speech": "tr-TR"
    },

    # North-East India regional language options.
    # Bodo, Khasi, Mizo and Meitei use Indian English as a
    # voice fallback where a dedicated voice is unavailable.
    "Assamese": {
        "code": "as",
        "speech": "as-IN"
    },

    "Bodo": {
        "code": "en",
        "speech": "en-IN"
    },

    "Khasi": {
        "code": "en",
        "speech": "en-IN"
    },

    "Mizo": {
        "code": "en",
        "speech": "en-IN"
    },

    "Meitei (Manipuri)": {
        "code": "en",
        "speech": "en-IN"
    }
}


# ============================================================
# UI TRANSLATIONS
# ============================================================

TRANSLATIONS = {

    "English": {

        "home": "Home",
        "games": "Cognitive Games",
        "reminders": "Reminders",
        "history": "My History",
        "details": "My Details",
        "reports": "Reports",
        "logout": "Logout",
        "welcome": "Welcome",
        "language": "Language",
        "save": "Save",
        "add": "Add",
        "delete": "Delete",
        "submit": "Submit",
        "start": "Start",
        "score": "Score",
        "difficulty": "Difficulty",
        "doctor": "Doctor",
        "patient": "Patient",
        "admin": "Administrator",
        "send_report": "Send Report",
        "select_patient": "Select Patient",
        "no_reports": "No reports available.",
        "no_history": "No game history available.",
        "success": "Success"
    },

    "Hindi": {

        "home": "होम",
        "games": "संज्ञानात्मक खेल",
        "reminders": "रिमाइंडर",
        "history": "मेरा इतिहास",
        "details": "मेरी जानकारी",
        "reports": "रिपोर्ट",
        "logout": "लॉगआउट",
        "welcome": "स्वागत है",
        "language": "भाषा",
        "save": "सेव करें",
        "add": "जोड़ें",
        "delete": "हटाएं",
        "submit": "सबमिट करें",
        "start": "शुरू करें",
        "score": "स्कोर",
        "difficulty": "कठिनाई",
        "doctor": "डॉक्टर",
        "patient": "मरीज",
        "admin": "एडमिन",
        "send_report": "रिपोर्ट भेजें",
        "select_patient": "मरीज चुनें",
        "no_reports": "कोई रिपोर्ट उपलब्ध नहीं है।",
        "no_history": "कोई गेम इतिहास उपलब्ध नहीं है।",
        "success": "सफलता"
    },

    "Marathi": {

        "home": "मुख्यपृष्ठ",
        "games": "संज्ञानात्मक खेळ",
        "reminders": "स्मरणपत्रे",
        "history": "माझा इतिहास",
        "details": "माझी माहिती",
        "reports": "अहवाल",
        "logout": "लॉगआउट",
        "welcome": "स्वागत आहे",
        "language": "भाषा",
        "save": "सेव्ह करा",
        "add": "जोडा",
        "delete": "हटवा",
        "submit": "सबमिट करा",
        "start": "सुरू करा",
        "score": "गुण",
        "difficulty": "अडचण",
        "doctor": "डॉक्टर",
        "patient": "रुग्ण",
        "admin": "प्रशासक",
        "send_report": "अहवाल पाठवा",
        "select_patient": "रुग्ण निवडा",
        "no_reports": "कोणताही अहवाल उपलब्ध नाही.",
        "no_history": "कोणताही गेम इतिहास उपलब्ध नाही.",
        "success": "यशस्वी"
    },

    "Gujarati": {

        "home": "હોમ",
        "games": "કોગ્નિટિવ ગેમ્સ",
        "reminders": "રિમાઇન્ડર્સ",
        "history": "મારો ઇતિહાસ",
        "details": "મારી માહિતી",
        "reports": "રિપોર્ટ્સ",
        "logout": "લોગઆઉટ",
        "welcome": "સ્વાગત છે",
        "language": "ભાષા",
        "save": "સેવ કરો",
        "add": "ઉમેરો",
        "delete": "કાઢી નાખો",
        "submit": "સબમિટ કરો",
        "start": "શરૂ કરો",
        "score": "સ્કોર",
        "difficulty": "મુશ્કેલી",
        "doctor": "ડોક્ટર",
        "patient": "દર્દી",
        "admin": "એડમિન",
        "send_report": "રિપોર્ટ મોકલો",
        "select_patient": "દર્દી પસંદ કરો",
        "no_reports": "કોઈ રિપોર્ટ ઉપલબ્ધ નથી.",
        "no_history": "કોઈ ગેમ ઇતિહાસ ઉપલબ્ધ નથી.",
        "success": "સફળ"
    },

    "Tamil": {

        "home": "முகப்பு",
        "games": "அறிவாற்றல் விளையாட்டுகள்",
        "reminders": "நினைவூட்டல்கள்",
        "history": "என் வரலாறு",
        "details": "என் விவரங்கள்",
        "reports": "அறிக்கைகள்",
        "logout": "வெளியேறு",
        "welcome": "வரவேற்கிறோம்",
        "language": "மொழி",
        "save": "சேமிக்கவும்",
        "add": "சேர்க்கவும்",
        "delete": "நீக்கவும்",
        "submit": "சமர்ப்பிக்கவும்",
        "start": "தொடங்கவும்",
        "score": "மதிப்பெண்",
        "difficulty": "சிரமம்",
        "doctor": "மருத்துவர்",
        "patient": "நோயாளர்",
        "admin": "நிர்வாகி",
        "send_report": "அறிக்கையை அனுப்பவும்",
        "select_patient": "நோயாளியைத் தேர்ந்தெடுக்கவும்",
        "no_reports": "அறிக்கைகள் இல்லை.",
        "no_history": "விளையாட்டு வரலாறு இல்லை.",
        "success": "வெற்றி"
    },

    "Telugu": {

        "home": "హోమ్",
        "games": "కాగ్నిటివ్ గేమ్స్",
        "reminders": "రిమైండర్లు",
        "history": "నా చరిత్ర",
        "details": "నా వివరాలు",
        "reports": "రిపోర్టులు",
        "logout": "లాగ్ అవుట్",
        "welcome": "స్వాగతం",
        "language": "భాష",
        "save": "సేవ్ చేయండి",
        "add": "జోడించండి",
        "delete": "తొలగించండి",
        "submit": "సమర్పించండి",
        "start": "ప్రారంభించండి",
        "score": "స్కోర్",
        "difficulty": "కష్టం",
        "doctor": "డాక్టర్",
        "patient": "రోగి",
        "admin": "అడ్మిన్",
        "send_report": "రిపోర్ట్ పంపండి",
        "select_patient": "రోగిని ఎంచుకోండి",
        "no_reports": "రిపోర్టులు లేవు.",
        "no_history": "గేమ్ చరిత్ర లేదు.",
        "success": "విజయం"
    },

    "Bengali": {

        "home": "হোম",
        "games": "কগনিটিভ গেম",
        "reminders": "রিমাইন্ডার",
        "history": "আমার ইতিহাস",
        "details": "আমার তথ্য",
        "reports": "রিপোর্ট",
        "logout": "লগআউট",
        "welcome": "স্বাগতম",
        "language": "ভাষা",
        "save": "সংরক্ষণ",
        "add": "যোগ করুন",
        "delete": "মুছুন",
        "submit": "জমা দিন",
        "start": "শুরু করুন",
        "score": "স্কোর",
        "difficulty": "কঠিনতা",
        "doctor": "ডাক্তার",
        "patient": "রোগী",
        "admin": "অ্যাডমিন",
        "send_report": "রিপোর্ট পাঠান",
        "select_patient": "রোগী নির্বাচন করুন",
        "no_reports": "কোনো রিপোর্ট নেই।",
        "no_history": "কোনো গেম ইতিহাস নেই।",
        "success": "সফল"
    }
}


def text(key, language):

    language_dict = TRANSLATIONS.get(
        language,
        TRANSLATIONS["English"]
    )

    return language_dict.get(
        key,
        TRANSLATIONS["English"].get(
            key,
            key
        )
    )


# ============================================================
# PASSWORD
# ============================================================

def hash_password(password):

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# ============================================================
# VOICE OUTPUT
# ============================================================

def generate_voice_html(
    message,
    language="English"
):

    if not message:
        return ""

    if gTTS is None:
        return ""

    try:

        audio_buffer = io.BytesIO()

        language_code = LANGUAGES.get(
            language,
            LANGUAGES["English"]
        )["code"]

        gTTS(
            text=message,
            lang=language_code,
            slow=False
        ).write_to_fp(
            audio_buffer
        )

        audio_buffer.seek(0)

        audio_base64 = base64.b64encode(
            audio_buffer.read()
        ).decode("utf-8")

        html = f"""
        <div style="
            width:1px;
            height:1px;
            overflow:hidden;
            position:absolute;
            left:-9999px;
            top:-9999px;
        ">

            <audio
                id="mindsetuVoice"
                autoplay
                playsinline
                preload="auto"
            >

                <source
                    src="data:audio/mpeg;base64,{audio_base64}"
                    type="audio/mpeg"
                >

            </audio>

            <script>

                const audio =
                    document.getElementById(
                        "mindsetuVoice"
                    );

                if (audio) {{

                    audio.volume = 1.0;

                    const playAudio = () => {{

                        audio.play().catch(
                            () => {{}}
                        );

                    }};

                    playAudio();

                }}

            </script>

        </div>
        """

        return html

    except Exception:
        return ""


def queue_voice(
    message,
    language="English"
):

    if not message:
        return

    st.session_state.pending_voice_message = (
        message
    )

    st.session_state.pending_voice_language = (
        language
    )


def play_pending_voice():

    message = st.session_state.get(
        "pending_voice_message"
    )

    language = st.session_state.get(
        "pending_voice_language",
        "English"
    )

    if not message:
        return

    # Clear first so the same message isn't played
    # on every rerun.
    st.session_state.pending_voice_message = None
    st.session_state.pending_voice_language = None

    html = generate_voice_html(
        message,
        language
    )

    if html:

        st.html(
            html,
            width=1,
            unsafe_allow_javascript=True
        )


def announce(
    message,
    language="English"
):

    # IMPORTANT:
    #
    # This function intentionally does NOT call:
    #
    # st.success()
    # st.info()
    # st.write()
    # st.audio()
    #
    # It is voice-only.

    queue_voice(
        message,
        language
    )


# ============================================================
# VOICE RECOGNITION
# ============================================================

def recognize_voice(
    audio_bytes,
    language
):
    if sr is None:
        return None, "SpeechRecognition package is not installed."
    if not audio_bytes:
        return None, "No audio was recorded. Please speak after starting the microphone."
    try:
        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.energy_threshold = 250
        recognizer.pause_threshold = 0.8
        recognizer.phrase_threshold = 0.2
        recognizer.non_speaking_duration = 0.5
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.25)
            except Exception:
                pass
            audio = recognizer.record(source)
        primary_language = LANGUAGES.get(language, LANGUAGES["English"])["speech"]
        languages_to_try = [primary_language]
        english_language = LANGUAGES["English"]["speech"]
        if primary_language != english_language:
            languages_to_try.append(english_language)
        for speech_language in languages_to_try:
            try:
                command = recognizer.recognize_google(audio, language=speech_language)
                command = re.sub(r"\s+", " ", command.lower().strip())
                if command:
                    return command, None
            except sr.UnknownValueError:
                continue
            except sr.RequestError:
                return None, "Speech recognition service is unavailable. Check your internet connection."
        return None, "I could not clearly understand your speech. Please speak louder and more slowly."
    except Exception as exc:
        return None, f"Voice input failed. Check microphone permission. ({type(exc).__name__})"


# ============================================================
# TIME PARSER
# ============================================================

def parse_time_from_command(command):

    if not command:
        return None

    # --------------------------------------------------------
    # 24-hour format
    #
    # 17:30
    # 09:15
    # --------------------------------------------------------

    match = re.search(
        r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b",
        command
    )

    if match:

        hour = int(
            match.group(1)
        )

        minute = int(
            match.group(2)
        )

        return f"{hour:02d}:{minute:02d}"

    # --------------------------------------------------------
    # 12-hour format
    #
    # 5 PM
    # 5:30 PM
    # 10 AM
    # --------------------------------------------------------

    match = re.search(
        r"\b(1[0-2]|0?[1-9])"
        r"(?:[:.]([0-5]\d))?"
        r"\s*(am|pm)\b",
        command,
        re.IGNORECASE
    )

    if match:

        hour = int(
            match.group(1)
        )

        minute = int(
            match.group(2) or 0
        )

        am_pm = match.group(3).lower()

        if am_pm == "pm" and hour != 12:
            hour += 12

        if am_pm == "am" and hour == 12:
            hour = 0

        return f"{hour:02d}:{minute:02d}"

    return None


# ============================================================
# REMINDER TITLE FROM VOICE COMMAND
# ============================================================

def extract_reminder_title(command):

    title = command.strip()

    phrases = [

        "add a reminder",
        "add reminder",

        "set a reminder",
        "set reminder",

        "create a reminder",
        "create reminder",

        "set a time for",
        "set time for",

        "remind me to",
        "remind me"
    ]

    for phrase in phrases:

        title = title.replace(
            phrase,
            ""
        )

    title = re.sub(
        r"\b(?:at|for)\s+"
        r"(?:[01]?\d|2[0-3])[:.][0-5]\d\b",
        "",
        title
    )

    title = re.sub(
        r"\b(?:at|for)\s+"
        r"(?:1[0-2]|0?[1-9])"
        r"(?:[:.][0-5]\d)?"
        r"\s*(?:am|pm)\b",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = title.strip()

    if not title:
        title = "Reminder"

    return title[0].upper() + title[1:]


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_SESSION_VALUES = {

    "logged_in": False,

    "user_id": None,

    "name": "",

    "username": "",

    "role": None,

    "language": "English",

    "doctor_id": None,

    "caretaker_id": None,

    "provider_role": None,

    "page": "home",

    "welcome_pending": False,

    "pending_voice_message": None,

    "pending_voice_language": None,

    "memory_sequence": None,

    "pattern_sequence": None,

    "reaction_target": None,

    "memory_round": 0,
    "memory_total_score": 0.0,
    "memory_start_time": None,
    "memory_answer_phase": False,
    "pattern_round": 0,
    "pattern_total_score": 0.0,
    "attention_round": 0,
    "attention_total_score": 0.0,

    # Image Recognition / Image Memory Game state.
    "image_memory_round": 0,
    "image_memory_total_score": 0.0,
    "image_memory_sequence": [],
    "image_memory_choices": [],
    "image_memory_start_time": None,
    "image_memory_answer_phase": False,
    "image_memory_selected": [],

    # Visible result message shown after a completed game.
    "game_result_message": None,
    "game_result_score": None,
    "game_result_old_difficulty": None,
    "game_result_new_difficulty": None
}


for key, value in DEFAULT_SESSION_VALUES.items():

    if key not in st.session_state:

        st.session_state[key] = value

# Backward-compatible image choice state for existing sessions.
if "image_memory_choices" not in st.session_state:
    st.session_state.image_memory_choices = []


# ============================================================
# PLAY PENDING VOICE
# ============================================================

if st.session_state.logged_in:

    play_pending_voice()


# ============================================================
# LOGIN / REGISTRATION
# ============================================================

if not st.session_state.logged_in:

    # Login / registration starts directly here.

    st.info(
        "MINDSETU NER is a prototype for "
        "cognitive wellness and performance tracking. "
        "It is not a medical diagnostic system."
    )

    login_tab, signup_tab, doctor_signup_tab, caretaker_signup_tab = st.tabs(
        [
            "🔐 Login",
            "📝 Patient Registration",
            "🩺 Doctor Registration",
            "🤝 Caretaker Registration"
        ]
    )

    # ========================================================
    # LOGIN
    # ========================================================

    with login_tab:

        st.subheader("Login")

        username = st.text_input(
            "Username",
            key="login_username"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "🔐 Login",
            type="primary",
            use_container_width=True
        ):

            username_clean = username.strip()

            # ------------------------------------------------
            # ADMIN
            # ------------------------------------------------

            if username_clean.lower() == "admin":

                if password == "admin123":

                    st.session_state.logged_in = True
                    st.session_state.user_id = 0
                    st.session_state.name = "Administrator"
                    st.session_state.username = "admin"
                    st.session_state.role = "admin"
                    st.session_state.provider_role = None
                    st.session_state.language = "English"
                    st.session_state.page = "home"

                    queue_voice(
                        "Welcome Administrator. "
                        "You have logged in successfully.",
                        "English"
                    )

                    st.rerun()

                else:

                    st.error(
                        "Incorrect admin password."
                    )

            # ------------------------------------------------
            # NORMAL USER
            # ------------------------------------------------

            else:

                user = conn.execute(
                    """
                    SELECT
                        id,
                        name,
                        username,
                        password_hash,
                        language,
                        role,
                        doctor_id,
                        adaptive_difficulty,
                        caretaker_id,
                        phone,
                        email,
                        location,
                        qualification,
                        qualification_status,
                        account_status
                    FROM users
                    WHERE LOWER(username)=LOWER(?)
                    """,
                    (username_clean,)
                ).fetchone()

                if user is None:

                    st.error(
                        "Username not found."
                    )

                elif hash_password(password) != user[3]:

                    st.error(
                        "Incorrect password."
                    )

                elif user[14] != "Active":

                    status_message = {
                        "Pending Verification": (
                            "Your account is waiting for administrator verification."
                        ),
                        "Rejected": (
                            "Your account was not approved. Please contact the administrator."
                        ),
                        "Inactive": (
                            "Your account is currently inactive. Please contact the administrator."
                        ),
                    }.get(
                        user[14],
                        "Your account is not active. Please contact the administrator."
                    )

                    st.error(status_message)

                else:

                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.name = user[1]
                    st.session_state.username = user[2]
                    st.session_state.language = user[4]
                    st.session_state.role = user[5]
                    st.session_state.doctor_id = user[6]
                    st.session_state.caretaker_id = user[8]
                    st.session_state.provider_role = (
                        user[5]
                        if user[5] in ("doctor", "caretaker")
                        else None
                    )
                    st.session_state.page = "home"

                    if user[5] == "patient":

                        queue_voice(
                            (
                                f"Welcome {user[1]}. "
                                "You have logged in successfully. "
                                "Now you can play cognitive games, "
                                "set reminders, check your history, "
                                "and listen to your reports."
                            ),
                            user[4]
                        )

                    elif user[5] == "doctor":

                        queue_voice(
                            (
                                f"Welcome Dr. {user[1]}. "
                                "You have logged in successfully. "
                                "You can manage your own patients "
                                "and review their performance."
                            ),
                            user[4]
                        )

                    elif user[5] == "caretaker":

                        queue_voice(
                            (
                                f"Welcome {user[1]}. "
                                "You have logged in successfully. "
                                "You can manage your own linked patients "
                                "and review their progress."
                            ),
                            user[4]
                        )

                    st.rerun()

    # ========================================================
    # PATIENT REGISTRATION - ORIGINAL FLOW KEPT
    # ========================================================

    with signup_tab:

        st.subheader(
            "Create Patient Account"
        )

        reg_name = st.text_input(
            "Full Name",
            key="reg_name"
        )

        reg_username = st.text_input(
            "Username",
            key="reg_username"
        )

        reg_password = st.text_input(
            "Password",
            type="password",
            key="reg_password"
        )

        reg_confirm = st.text_input(
            "Confirm Password",
            type="password",
            key="reg_confirm"
        )

        reg_phone = st.text_input(
            "Phone Number (optional)",
            key="reg_phone"
        )

        reg_email = st.text_input(
            "Email ID (optional)",
            key="reg_email"
        )

        reg_location = st.text_input(
            "Location (optional)",
            key="reg_location"
        )

        reg_language = st.selectbox(
            "Select Language",
            list(LANGUAGES.keys()),
            key="reg_language"
        )

        if st.button(
            "📝 Create Patient Account",
            type="primary",
            use_container_width=True
        ):

            if not reg_name.strip():

                st.error("Please enter your name.")

            elif not reg_username.strip():

                st.error("Please enter a username.")

            elif len(reg_password) < 6:

                st.error("Password must contain at least 6 characters.")

            elif reg_password != reg_confirm:

                st.error("Passwords do not match.")

            elif reg_phone.strip() and not phone_is_valid(reg_phone):

                st.error("Please enter a valid phone number.")

            elif reg_email.strip() and not email_is_valid(reg_email):

                st.error("Please enter a valid email address.")

            else:

                existing = conn.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE LOWER(username)=LOWER(?)
                    """,
                    (reg_username.strip(),)
                ).fetchone()

                if existing:

                    st.error("Username already exists.")

                else:

                    conn.execute(
                        """
                        INSERT INTO users(
                            name,
                            username,
                            password_hash,
                            language,
                            baseline,
                            role,
                            adaptive_difficulty,
                            phone,
                            email,
                            location,
                            account_status,
                            created_at
                        )
                        VALUES(
                            ?, ?, ?, ?, 0, 'patient', 1, ?, ?, ?, 'Active', ?
                        )
                        """,
                        (
                            reg_name.strip(),
                            reg_username.strip(),
                            hash_password(reg_password),
                            reg_language,
                            reg_phone.strip(),
                            reg_email.strip(),
                            normalize_location(reg_location),
                            datetime.now().isoformat(timespec="seconds")
                        )
                    )

                    conn.commit()

                    st.success(
                        "Patient account created successfully."
                    )

                    queue_voice(
                        (
                            f"Welcome {reg_name.strip()}. "
                            "Your patient account has been created successfully."
                        ),
                        reg_language
                    )

                    play_pending_voice()

    # ========================================================
    # DOCTOR REGISTRATION
    # ========================================================

    with doctor_signup_tab:

        st.subheader("🩺 Doctor Registration")
        st.info(
            "Doctor registrations require qualification details. "
            "The account remains pending until the administrator verifies the submitted qualification."
        )

        doc_name = st.text_input("Full Name", key="doctor_reg_name")
        doc_username = st.text_input("Username", key="doctor_reg_username")
        doc_password = st.text_input("Password", type="password", key="doctor_reg_password")
        doc_confirm = st.text_input("Confirm Password", type="password", key="doctor_reg_confirm")
        doc_phone = st.text_input("Phone Number", key="doctor_reg_phone")
        doc_email = st.text_input("Email ID", key="doctor_reg_email")
        doc_location = st.text_input("Location / Clinic Location", key="doctor_reg_location")
        doc_qualification = st.text_input(
            "Degree / Qualification",
            placeholder="Example: MBBS, MD, BDS, etc.",
            key="doctor_reg_qualification"
        )
        doc_qualification_number = st.text_input(
            "Medical Registration / Qualification Number",
            key="doctor_reg_qualification_number"
        )
        doc_document = st.file_uploader(
            "Upload Degree / Qualification Document",
            type=["pdf", "png", "jpg", "jpeg"],
            key="doctor_reg_document"
        )
        doc_language = st.selectbox(
            "Preferred Language",
            list(LANGUAGES.keys()),
            key="doctor_reg_language"
        )

        if st.button(
            "🩺 Submit Doctor Registration",
            type="primary",
            use_container_width=True
        ):

            if not doc_name.strip():
                st.error("Please enter the doctor's name.")
            elif not doc_username.strip():
                st.error("Please enter a username.")
            elif len(doc_password) < 6:
                st.error("Password must contain at least 6 characters.")
            elif doc_password != doc_confirm:
                st.error("Passwords do not match.")
            elif not phone_is_valid(doc_phone):
                st.error("Please enter a valid phone number.")
            elif not email_is_valid(doc_email):
                st.error("Please enter a valid email address.")
            elif not normalize_location(doc_location):
                st.error("Please enter the doctor's location.")
            elif not doc_qualification.strip():
                st.error("Please enter a degree or qualification.")
            elif not doc_qualification_number.strip():
                st.error("Please enter the medical registration/qualification number.")
            elif doc_document is None:
                st.error("Please upload the degree/qualification document.")
            else:

                existing = conn.execute(
                    "SELECT id FROM users WHERE LOWER(username)=LOWER(?)",
                    (doc_username.strip(),)
                ).fetchone()

                if existing:
                    st.error("Username already exists.")
                else:

                    conn.execute(
                        """
                        INSERT INTO users(
                            name, username, password_hash, language, baseline,
                            role, adaptive_difficulty, phone, email, location,
                            qualification, qualification_number, qualification_document,
                            qualification_status, account_status, created_at
                        )
                        VALUES(
                            ?, ?, ?, ?, 0, 'doctor', 1, ?, ?, ?, ?, ?, ?,
                            'Pending', 'Pending Verification', ?
                        )
                        """,
                        (
                            doc_name.strip(),
                            doc_username.strip(),
                            hash_password(doc_password),
                            doc_language,
                            doc_phone.strip(),
                            doc_email.strip(),
                            normalize_location(doc_location),
                            doc_qualification.strip(),
                            doc_qualification_number.strip(),
                            doc_document.name,
                            datetime.now().isoformat(timespec="seconds")
                        )
                    )
                    conn.commit()

                    st.success(
                        "Doctor registration submitted. Please wait for administrator verification."
                    )
                    announce(
                        "Doctor registration submitted successfully and is waiting for administrator verification.",
                        doc_language
                    )

    # ========================================================
    # CARETAKER REGISTRATION
    # ========================================================

    with caretaker_signup_tab:

        st.subheader("🤝 Caretaker Registration")
        st.info(
            "Caretakers can create accounts and later add their own patients directly from their portal."
        )

        care_name = st.text_input("Full Name", key="caretaker_reg_name")
        care_username = st.text_input("Username", key="caretaker_reg_username")
        care_password = st.text_input("Password", type="password", key="caretaker_reg_password")
        care_confirm = st.text_input("Confirm Password", type="password", key="caretaker_reg_confirm")
        care_phone = st.text_input("Phone Number", key="caretaker_reg_phone")
        care_email = st.text_input("Email ID", key="caretaker_reg_email")
        care_location = st.text_input("Location", key="caretaker_reg_location")
        care_relationship = st.text_input(
            "Relationship / Care Role",
            placeholder="Example: Family Caretaker, Home Care Assistant",
            key="caretaker_reg_relationship"
        )
        care_language = st.selectbox(
            "Preferred Language",
            list(LANGUAGES.keys()),
            key="caretaker_reg_language"
        )

        if st.button(
            "🤝 Create Caretaker Account",
            type="primary",
            use_container_width=True
        ):

            if not care_name.strip():
                st.error("Please enter the caretaker's name.")
            elif not care_username.strip():
                st.error("Please enter a username.")
            elif len(care_password) < 6:
                st.error("Password must contain at least 6 characters.")
            elif care_password != care_confirm:
                st.error("Passwords do not match.")
            elif not phone_is_valid(care_phone):
                st.error("Please enter a valid phone number.")
            elif not email_is_valid(care_email):
                st.error("Please enter a valid email address.")
            elif not normalize_location(care_location):
                st.error("Please enter the caretaker's location.")
            else:

                existing = conn.execute(
                    "SELECT id FROM users WHERE LOWER(username)=LOWER(?)",
                    (care_username.strip(),)
                ).fetchone()

                if existing:
                    st.error("Username already exists.")
                else:

                    # Store the care role in qualification for backward-compatible schema usage.
                    conn.execute(
                        """
                        INSERT INTO users(
                            name, username, password_hash, language, baseline,
                            role, adaptive_difficulty, phone, email, location,
                            qualification, qualification_status, account_status, created_at
                        )
                        VALUES(
                            ?, ?, ?, ?, 0, 'caretaker', 1, ?, ?, ?, ?,
                            'Not Required', 'Active', ?
                        )
                        """,
                        (
                            care_name.strip(),
                            care_username.strip(),
                            hash_password(care_password),
                            care_language,
                            care_phone.strip(),
                            care_email.strip(),
                            normalize_location(care_location),
                            care_relationship.strip(),
                            datetime.now().isoformat(timespec="seconds")
                        )
                    )
                    conn.commit()

                    st.success(
                        "Caretaker account created successfully."
                    )
                    announce(
                        "Caretaker account created successfully. You can now log in and add your own patients.",
                        care_language
                    )

    st.stop()


# ============================================================
# CURRENT SESSION USER
# ============================================================

role = st.session_state.role
user_id = st.session_state.user_id
name = st.session_state.name
language = st.session_state.language


# ============================================================
# ADMIN DASHBOARD
# ============================================================

if role == "admin":

    st.title(
        "👑 MINDSETU NER — Administrator Dashboard"
    )

    admin_tabs = st.tabs(
        [
            "📊 Overview",
            "👥 Patients",
            "🩺 Doctors",
            "🤝 Caretakers",
            "✅ Verification & Management",
            "🎮 All Sessions",
            "📄 All Reports"
        ]
    )

    # ========================================================
    # OVERVIEW
    # ========================================================

    with admin_tabs[0]:

        patient_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='patient'"
        ).fetchone()[0]

        doctor_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='doctor'"
        ).fetchone()[0]

        caretaker_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='caretaker'"
        ).fetchone()[0]

        pending_doctors = conn.execute(
            """
            SELECT COUNT(*)
            FROM users
            WHERE role='doctor'
            AND account_status='Pending Verification'
            """
        ).fetchone()[0]

        session_count = conn.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]

        report_count = conn.execute(
            "SELECT COUNT(*) FROM reports"
        ).fetchone()[0]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Patients", patient_count)
        c2.metric("Doctors", doctor_count)
        c3.metric("Caretakers", caretaker_count)
        c4.metric("Pending Doctor Verification", pending_doctors)
        c5.metric("Game Sessions", session_count)

        st.metric("Reports", report_count)

        st.info(
            "The administrator manages registration, verification and account status. "
            "Patient-to-doctor/caretaker linking is created directly by the provider who adds the patient; "
            "there is no manual central patient assignment workflow."
        )

    # ========================================================
    # PATIENTS
    # ========================================================

    with admin_tabs[1]:

        patients = conn.execute(
            """
            SELECT
                id, name, username, language, baseline,
                doctor_id, caretaker_id, adaptive_difficulty,
                phone, email, location
            FROM users
            WHERE role='patient'
            ORDER BY name
            """
        ).fetchall()

        patient_data = []
        for patient_row in patients:

            doctor_name = "Not assigned"
            caretaker_name = "Not assigned"

            if patient_row[5]:
                d = conn.execute(
                    "SELECT name FROM users WHERE id=? AND role='doctor'",
                    (patient_row[5],)
                ).fetchone()
                if d:
                    doctor_name = "Dr. " + d[0]

            if patient_row[6]:
                c = conn.execute(
                    "SELECT name FROM users WHERE id=? AND role='caretaker'",
                    (patient_row[6],)
                ).fetchone()
                if c:
                    caretaker_name = c[0]

            patient_data.append(
                {
                    "ID": patient_row[0],
                    "Name": patient_row[1],
                    "Username": patient_row[2],
                    "Language": patient_row[3],
                    "Baseline": patient_row[4],
                    "Difficulty": patient_row[7],
                    "Phone": patient_row[8],
                    "Email": patient_row[9],
                    "Location": patient_row[10],
                    "Doctor": doctor_name,
                    "Caretaker": caretaker_name,
                }
            )

        if patient_data:
            st.dataframe(
                patient_data,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No patients registered.")

    # ========================================================
    # DOCTORS - MANAGEMENT ONLY
    # ========================================================

    with admin_tabs[2]:

        doctors = conn.execute(
            """
            SELECT
                id, name, username, phone, email, location,
                qualification, qualification_number,
                qualification_status, account_status, created_at
            FROM users
            WHERE role='doctor'
            ORDER BY name
            """
        ).fetchall()

        if doctors:
            st.dataframe(
                [
                    {
                        "ID": d[0],
                        "Doctor": d[1],
                        "Username": d[2],
                        "Phone": d[3],
                        "Email": d[4],
                        "Location": d[5],
                        "Qualification": d[6],
                        "Registration No.": d[7],
                        "Qualification Status": d[8],
                        "Account Status": d[9],
                        "Created": d[10],
                    }
                    for d in doctors
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No doctor registrations yet.")

    # ========================================================
    # CARETAKERS - MANAGEMENT
    # ========================================================

    with admin_tabs[3]:

        caretakers = conn.execute(
            """
            SELECT
                id, name, username, phone, email, location,
                qualification, account_status, created_at
            FROM users
            WHERE role='caretaker'
            ORDER BY name
            """
        ).fetchall()

        if caretakers:
            st.dataframe(
                [
                    {
                        "ID": c[0],
                        "Caretaker": c[1],
                        "Username": c[2],
                        "Phone": c[3],
                        "Email": c[4],
                        "Location": c[5],
                        "Care Role": c[6],
                        "Account Status": c[7],
                        "Created": c[8],
                    }
                    for c in caretakers
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No caretaker registrations yet.")

    # ========================================================
    # VERIFICATION & MANAGEMENT
    # ========================================================

    with admin_tabs[4]:

        st.subheader("✅ Doctor Qualification Verification")

        pending_doctors = conn.execute(
            """
            SELECT
                id, name, username, phone, email, location,
                qualification, qualification_number,
                qualification_document, qualification_status,
                account_status, created_at
            FROM users
            WHERE role='doctor'
            AND qualification_status='Pending'
            ORDER BY created_at DESC
            """
        ).fetchall()

        if not pending_doctors:
            st.success("No doctor qualifications are waiting for verification.")
        else:
            for d in pending_doctors:
                with st.expander(
                    f"🩺 {d[1]} — {d[6]} — Registration No. {d[7]}"
                ):
                    st.write(f"**Username:** {d[2]}")
                    st.write(f"**Phone:** {d[3]}")
                    st.write(f"**Email:** {d[4]}")
                    st.write(f"**Location:** {d[5]}")
                    st.write(f"**Qualification:** {d[6]}")
                    st.write(f"**Registration Number:** {d[7]}")
                    st.write(f"**Uploaded Document:** {d[8]}")
                    st.write(f"**Submitted:** {d[11]}")

                    verify_col, reject_col = st.columns(2)

                    with verify_col:
                        if st.button(
                            "✅ Verify & Activate Doctor",
                            key=f"verify_doctor_{d[0]}",
                            use_container_width=True,
                            type="primary"
                        ):
                            conn.execute(
                                """
                                UPDATE users
                                SET qualification_status='Verified',
                                    account_status='Active'
                                WHERE id=? AND role='doctor'
                                """,
                                (d[0],)
                            )
                            conn.commit()
                            announce(
                                "Doctor qualification verified and account activated.",
                                "English"
                            )
                            st.rerun()

                    with reject_col:
                        if st.button(
                            "❌ Reject Verification",
                            key=f"reject_doctor_{d[0]}",
                            use_container_width=True
                        ):
                            conn.execute(
                                """
                                UPDATE users
                                SET qualification_status='Rejected',
                                    account_status='Rejected'
                                WHERE id=? AND role='doctor'
                                """,
                                (d[0],)
                            )
                            conn.commit()
                            announce(
                                "Doctor qualification verification was rejected.",
                                "English"
                            )
                            st.rerun()

        st.divider()
        st.subheader("👥 Account Status Management")

        managed_users = conn.execute(
            """
            SELECT id, name, username, role, account_status, qualification_status
            FROM users
            WHERE role IN ('doctor', 'caretaker')
            ORDER BY role, name
            """
        ).fetchall()

        for u in managed_users:
            m1, m2, m3, m4 = st.columns([3, 2, 2, 2])
            m1.write(f"**{u[1]}** ({u[2]})")
            m2.write(u[3].title())
            m3.write(u[4])
            with m4:
                action_label = "Deactivate" if u[4] == "Active" else "Activate"
                if st.button(
                    action_label,
                    key=f"status_{u[0]}",
                    use_container_width=True
                ):
                    new_status = "Inactive" if u[4] == "Active" else "Active"
                    conn.execute(
                        "UPDATE users SET account_status=? WHERE id=? AND role IN ('doctor','caretaker')",
                        (new_status, u[0])
                    )
                    conn.commit()
                    st.rerun()

        st.divider()
        st.warning(
            "Central manual patient assignment has been removed. "
            "The system now relies on Doctor/Caretaker → Add Patient onboarding, "
            "which automatically links the new patient to the provider who created the account."
        )

    # ========================================================
    # ALL SESSIONS
    # ========================================================

    with admin_tabs[5]:

        sessions = conn.execute(
            """
            SELECT
                u.name,
                u.username,
                s.game,
                s.score,
                s.difficulty,
                s.created_at
            FROM sessions s
            INNER JOIN users u
            ON s.user_id=u.id
            ORDER BY s.id DESC
            """
        ).fetchall()

        if sessions:
            st.dataframe(
                [
                    {
                        "Patient": row[0],
                        "Username": row[1],
                        "Game": row[2],
                        "Score": row[3],
                        "Difficulty": row[4],
                        "Date": row[5]
                    }
                    for row in sessions
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No sessions available.")

    # ========================================================
    # ALL REPORTS
    # ========================================================

    with admin_tabs[6]:

        reports = conn.execute(
            """
            SELECT
                r.created_at,
                p.name,
                d.name,
                r.title,
                r.report_text
            FROM reports r
            INNER JOIN users p
            ON r.patient_id=p.id
            INNER JOIN users d
            ON r.doctor_id=d.id
            ORDER BY r.id DESC
            """
        ).fetchall()

        if reports:
            for report in reports:
                with st.expander(
                    f"{report[1]} — {report[3]}"
                ):
                    st.write(f"Doctor: Dr. {report[2]}")
                    st.write(f"Date: {report[0]}")
                    st.write(report[4])
        else:
            st.info("No reports available.")

    st.divider()

    if st.button(
        "🚪 Logout",
        key="admin_logout"
    ):
        st.session_state.clear()
        st.rerun()

    st.stop()


# ============================================================
# DOCTOR DASHBOARD
# ============================================================

if role == "doctor":

    st.title(
        f"🩺 Doctor Portal — Dr. {name}"
    )

    doctor_profile = conn.execute(
        """
        SELECT
            phone, email, location, qualification,
            qualification_number, qualification_status,
            account_status
        FROM users
        WHERE id=? AND role='doctor'
        """,
        (user_id,)
    ).fetchone()

    doctor_tabs = st.tabs(
        [
            "🏠 Overview",
            "➕ Add Patient",
            "👥 My Patients",
            "📊 Patient Performance",
            "📄 Send Report",
            "👤 My Profile"
        ]
    )

    assigned_patients = conn.execute(
        """
        SELECT
            id, name, username, language, baseline,
            phone, email, location, adaptive_difficulty
        FROM users
        WHERE role='patient'
        AND doctor_id=?
        ORDER BY name
        """,
        (user_id,)
    ).fetchall()

    # ========================================================
    # DOCTOR OVERVIEW
    # ========================================================

    with doctor_tabs[0]:

        c1, c2, c3 = st.columns(3)
        c1.metric("My Patients", len(assigned_patients))
        c2.metric("Your Role", "Doctor")
        c3.metric(
            "Qualification",
            doctor_profile[4] if doctor_profile and doctor_profile[5] == "Verified" else "Pending"
        )

        st.success(
            "✅ Doctor account is active. Patient data is restricted to patients created/linked under your account."
        )

        st.info(
            "Doctor onboarding model: use **Add Patient** to create a new patient account. "
            "The new patient is automatically linked to you. No administrator assignment is required."
        )

        st.warning(
            "🎮 Cognitive games are not available for doctor accounts."
        )

    # ========================================================
    # ADD PATIENT - AUTOMATICALLY LINKED TO THIS DOCTOR
    # ========================================================

    with doctor_tabs[1]:

        st.subheader("➕ Add Patient")
        st.caption(
            "A patient created here is automatically linked to you and will appear in My Patients."
        )

        with st.form("doctor_add_patient_form"):
            patient_name = st.text_input("Patient Full Name", key="doctor_add_patient_name")
            patient_username = st.text_input("Patient Username", key="doctor_add_patient_username")
            patient_password = st.text_input("Patient Password", type="password", key="doctor_add_patient_password")
            patient_confirm = st.text_input("Confirm Password", type="password", key="doctor_add_patient_confirm")
            patient_phone = st.text_input("Phone Number", key="doctor_add_patient_phone")
            patient_email = st.text_input("Email ID", key="doctor_add_patient_email")
            patient_location = st.text_input("Location", key="doctor_add_patient_location")
            patient_language = st.selectbox(
                "Language",
                list(LANGUAGES.keys()),
                key="doctor_add_patient_language"
            )

            submitted = st.form_submit_button(
                "➕ Add Patient & Link Automatically",
                type="primary",
                use_container_width=True
            )

        if submitted:

            if not patient_name.strip():
                st.error("Please enter the patient's name.")
            elif not patient_username.strip():
                st.error("Please enter a patient username.")
            elif len(patient_password) < 6:
                st.error("Patient password must contain at least 6 characters.")
            elif patient_password != patient_confirm:
                st.error("Passwords do not match.")
            elif not phone_is_valid(patient_phone):
                st.error("Please enter a valid patient phone number.")
            elif not email_is_valid(patient_email):
                st.error("Please enter a valid patient email address.")
            elif not normalize_location(patient_location):
                st.error("Please enter the patient's location.")
            else:

                existing = conn.execute(
                    "SELECT id FROM users WHERE LOWER(username)=LOWER(?)",
                    (patient_username.strip(),)
                ).fetchone()

                if existing:
                    st.error("Username already exists.")
                else:

                    conn.execute(
                        """
                        INSERT INTO users(
                            name, username, password_hash, language,
                            baseline, role, adaptive_difficulty,
                            doctor_id, caretaker_id, phone, email, location,
                            account_status, created_by_id, created_at
                        )
                        VALUES(
                            ?, ?, ?, ?, 0, 'patient', 1,
                            ?, NULL, ?, ?, ?, 'Active', ?, ?
                        )
                        """,
                        (
                            patient_name.strip(),
                            patient_username.strip(),
                            hash_password(patient_password),
                            patient_language,
                            user_id,
                            patient_phone.strip(),
                            patient_email.strip(),
                            normalize_location(patient_location),
                            user_id,
                            datetime.now().isoformat(timespec="seconds")
                        )
                    )
                    conn.commit()

                    announce(
                        f"Patient {patient_name.strip()} was added and automatically linked to you.",
                        language
                    )
                    st.success(
                        f"Patient {patient_name.strip()} created successfully and linked to you."
                    )
                    st.rerun()

    # ========================================================
    # DOCTOR OWN PATIENTS
    # ========================================================

    with doctor_tabs[2]:

        if assigned_patients:
            st.dataframe(
                [
                    {
                        "Patient": p[1],
                        "Username": p[2],
                        "Language": p[3],
                        "Baseline": p[4],
                        "Phone": p[5],
                        "Email": p[6],
                        "Location": p[7],
                        "Difficulty": p[8]
                    }
                    for p in assigned_patients
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No patients have been added to your account yet.")

    # ========================================================
    # DOCTOR PATIENT PERFORMANCE
    # ========================================================

    with doctor_tabs[3]:

        if assigned_patients:

            patient_map = {
                f"{p[1]} ({p[2]})": p[0]
                for p in assigned_patients
            }

            selected_patient_name = st.selectbox(
                "Select Patient",
                list(patient_map.keys()),
                key="doctor_view_patient"
            )

            selected_patient_id = patient_map[selected_patient_name]

            # Server-side privacy check.
            if not provider_can_manage_patient(
                user_id,
                "doctor",
                selected_patient_id
            ):
                st.error("You are not authorized to access this patient.")
            else:

                patient_data = conn.execute(
                    """
                    SELECT
                        id, name, username, language,
                        baseline, adaptive_difficulty,
                        phone, email, location
                    FROM users
                    WHERE id=?
                    AND role='patient'
                    AND doctor_id=?
                    """,
                    (selected_patient_id, user_id)
                ).fetchone()

                if patient_data:

                    st.subheader(f"👤 {patient_data[1]}")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Baseline", f"{patient_data[4]:.1f}")
                    c2.metric("Difficulty", patient_data[5])

                    sessions = conn.execute(
                        """
                        SELECT game, score, difficulty, created_at
                        FROM sessions
                        WHERE user_id=?
                        ORDER BY id DESC
                        """,
                        (selected_patient_id,)
                    ).fetchall()

                    scores = [float(s[1]) for s in sessions]
                    average_score = sum(scores) / len(scores) if scores else 0
                    best_score = max(scores) if scores else 0

                    c3.metric("Average Score", f"{average_score:.1f}")
                    st.metric("Best Score", f"{best_score:.1f}")

                    st.write(f"**Phone:** {patient_data[6]}")
                    st.write(f"**Email:** {patient_data[7]}")
                    st.write(f"**Location:** {patient_data[8]}")

                    if sessions:
                        st.subheader("📊 Game Performance")
                        st.dataframe(
                            [
                                {
                                    "Game": s[0],
                                    "Score": s[1],
                                    "Difficulty": s[2],
                                    "Date": s[3]
                                }
                                for s in sessions
                            ],
                            use_container_width=True,
                            hide_index=True
                        )

                        progress_df = pd.DataFrame(
                            [
                                {
                                    "Session": idx,
                                    "Score": float(s[1])
                                }
                                for idx, s in enumerate(reversed(sessions[-5:]), start=1)
                            ]
                        )
                        if not progress_df.empty:
                            st.line_chart(
                                progress_df.set_index("Session"),
                                y="Score",
                                use_container_width=True
                            )
                    else:
                        st.info("No game sessions recorded.")

    # ========================================================
    # DOCTOR REPORTS
    # ========================================================

    with doctor_tabs[4]:

        if assigned_patients:

            patient_map = {
                f"{p[1]} ({p[2]})": p[0]
                for p in assigned_patients
            }

            selected_report_patient = st.selectbox(
                "Select Patient",
                list(patient_map.keys()),
                key="doctor_report_patient"
            )

            report_patient_id = patient_map[selected_report_patient]

            if provider_can_manage_patient(
                user_id,
                "doctor",
                report_patient_id
            ):

                sessions = conn.execute(
                    "SELECT score FROM sessions WHERE user_id=?",
                    (report_patient_id,)
                ).fetchall()

                report_scores = [float(row[0]) for row in sessions]
                report_average = sum(report_scores) / len(report_scores) if report_scores else 0
                report_best = max(report_scores) if report_scores else 0

                st.write(f"Completed sessions: **{len(report_scores)}**")
                st.write(f"Average score: **{report_average:.1f}**")
                st.write(f"Best score: **{report_best:.1f}**")

                report_title = st.text_input(
                    "Report Title",
                    value="Overall Performance Report",
                    key="report_title"
                )

                report_text = st.text_area(
                    "Overall Performance Report",
                    value=(
                        "Overall Performance Report\n\n"
                        f"Total sessions: {len(report_scores)}\n"
                        f"Average score: {report_average:.1f}\n"
                        f"Best score: {report_best:.1f}\n\n"
                        "Doctor's observations:\n"
                    ),
                    height=280,
                    key="report_text"
                )

                if st.button(
                    "📤 Send Report to Patient",
                    type="primary"
                ):

                    if not report_text.strip():
                        st.error("Report cannot be empty.")
                    else:
                        conn.execute(
                            """
                            INSERT INTO reports(
                                patient_id,
                                doctor_id,
                                title,
                                report_text,
                                created_at,
                                status
                            )
                            VALUES(?, ?, ?, ?, ?, 'Sent')
                            """,
                            (
                                report_patient_id,
                                user_id,
                                report_title.strip(),
                                report_text.strip(),
                                datetime.now().isoformat(timespec="seconds")
                            )
                        )
                        conn.commit()
                        announce(
                            "Overall performance report sent successfully to the patient.",
                            "English"
                        )
                        st.rerun()

        else:
            st.info("Add patients before sending reports.")

    # ========================================================
    # DOCTOR PROFILE
    # ========================================================

    with doctor_tabs[5]:

        if doctor_profile:
            st.write(f"**Phone:** {doctor_profile[0]}")
            st.write(f"**Email:** {doctor_profile[1]}")
            st.write(f"**Location:** {doctor_profile[2]}")
            st.write(f"**Qualification:** {doctor_profile[3]}")
            st.write(f"**Registration Number:** {doctor_profile[4]}")
            st.write(f"**Qualification Verification:** {doctor_profile[5]}")
            st.write(f"**Account Status:** {doctor_profile[6]}")

    st.divider()

    if st.button(
        "🚪 Logout",
        key="doctor_logout"
    ):
        st.session_state.clear()
        st.rerun()

    st.stop()


# ============================================================
# CARETAKER DASHBOARD
# ============================================================

if role == "caretaker":

    st.title(
        f"🤝 Caretaker Portal — {name}"
    )

    caretaker_profile = conn.execute(
        """
        SELECT phone, email, location, qualification, account_status
        FROM users
        WHERE id=? AND role='caretaker'
        """,
        (user_id,)
    ).fetchone()

    caretaker_tabs = st.tabs(
        [
            "🏠 Overview",
            "➕ Add Patient",
            "👥 My Patients",
            "📊 Patient Performance",
            "🔔 Patient Reminders",
            "👤 My Profile"
        ]
    )

    own_patients = conn.execute(
        """
        SELECT
            id, name, username, language, baseline,
            phone, email, location, adaptive_difficulty
        FROM users
        WHERE role='patient'
        AND caretaker_id=?
        ORDER BY name
        """,
        (user_id,)
    ).fetchall()

    with caretaker_tabs[0]:

        c1, c2 = st.columns(2)
        c1.metric("My Patients", len(own_patients))
        c2.metric("Your Role", "Caretaker")

        st.success(
            "✅ Caretaker access is limited to patients linked to your account."
        )
        st.info(
            "Use **Add Patient** to create a patient account. "
            "The patient is automatically linked to you."
        )
        st.warning(
            "🎮 Cognitive games are available only to patient accounts."
        )

    with caretaker_tabs[1]:

        st.subheader("➕ Add Patient")
        st.caption(
            "The new patient will automatically belong to your caretaker account."
        )

        with st.form("caretaker_add_patient_form"):
            patient_name = st.text_input("Patient Full Name", key="caretaker_add_patient_name")
            patient_username = st.text_input("Patient Username", key="caretaker_add_patient_username")
            patient_password = st.text_input("Patient Password", type="password", key="caretaker_add_patient_password")
            patient_confirm = st.text_input("Confirm Password", type="password", key="caretaker_add_patient_confirm")
            patient_phone = st.text_input("Phone Number", key="caretaker_add_patient_phone")
            patient_email = st.text_input("Email ID", key="caretaker_add_patient_email")
            patient_location = st.text_input("Location", key="caretaker_add_patient_location")
            patient_language = st.selectbox(
                "Language",
                list(LANGUAGES.keys()),
                key="caretaker_add_patient_language"
            )

            submitted = st.form_submit_button(
                "➕ Add Patient & Link Automatically",
                type="primary",
                use_container_width=True
            )

        if submitted:

            if not patient_name.strip():
                st.error("Please enter the patient's name.")
            elif not patient_username.strip():
                st.error("Please enter a patient username.")
            elif len(patient_password) < 6:
                st.error("Patient password must contain at least 6 characters.")
            elif patient_password != patient_confirm:
                st.error("Passwords do not match.")
            elif not phone_is_valid(patient_phone):
                st.error("Please enter a valid patient phone number.")
            elif not email_is_valid(patient_email):
                st.error("Please enter a valid patient email address.")
            elif not normalize_location(patient_location):
                st.error("Please enter the patient's location.")
            else:

                existing = conn.execute(
                    "SELECT id FROM users WHERE LOWER(username)=LOWER(?)",
                    (patient_username.strip(),)
                ).fetchone()

                if existing:
                    st.error("Username already exists.")
                else:
                    conn.execute(
                        """
                        INSERT INTO users(
                            name, username, password_hash, language,
                            baseline, role, adaptive_difficulty,
                            doctor_id, caretaker_id, phone, email, location,
                            account_status, created_by_id, created_at
                        )
                        VALUES(
                            ?, ?, ?, ?, 0, 'patient', 1,
                            NULL, ?, ?, ?, ?, 'Active', ?, ?
                        )
                        """,
                        (
                            patient_name.strip(),
                            patient_username.strip(),
                            hash_password(patient_password),
                            patient_language,
                            user_id,
                            patient_phone.strip(),
                            patient_email.strip(),
                            normalize_location(patient_location),
                            user_id,
                            datetime.now().isoformat(timespec="seconds")
                        )
                    )
                    conn.commit()

                    announce(
                        f"Patient {patient_name.strip()} was added and automatically linked to you.",
                        language
                    )
                    st.success(
                        f"Patient {patient_name.strip()} created successfully and linked to you."
                    )
                    st.rerun()

    with caretaker_tabs[2]:

        if own_patients:
            st.dataframe(
                [
                    {
                        "Patient": p[1],
                        "Username": p[2],
                        "Language": p[3],
                        "Baseline": p[4],
                        "Phone": p[5],
                        "Email": p[6],
                        "Location": p[7],
                        "Difficulty": p[8]
                    }
                    for p in own_patients
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No patients have been added to your caretaker account yet.")

    with caretaker_tabs[3]:

        if own_patients:

            patient_map = {
                f"{p[1]} ({p[2]})": p[0]
                for p in own_patients
            }

            selected_patient_name = st.selectbox(
                "Select Patient",
                list(patient_map.keys()),
                key="caretaker_view_patient"
            )

            selected_patient_id = patient_map[selected_patient_name]

            if not provider_can_manage_patient(
                user_id,
                "caretaker",
                selected_patient_id
            ):
                st.error("You are not authorized to access this patient.")
            else:

                patient_data = conn.execute(
                    """
                    SELECT
                        id, name, username, language,
                        baseline, adaptive_difficulty,
                        phone, email, location
                    FROM users
                    WHERE id=?
                    AND role='patient'
                    AND caretaker_id=?
                    """,
                    (selected_patient_id, user_id)
                ).fetchone()

                if patient_data:
                    st.subheader(f"👤 {patient_data[1]}")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Baseline", f"{patient_data[4]:.1f}")
                    c2.metric("Difficulty", patient_data[5])

                    sessions = conn.execute(
                        """
                        SELECT game, score, difficulty, created_at
                        FROM sessions
                        WHERE user_id=?
                        ORDER BY id DESC
                        """,
                        (selected_patient_id,)
                    ).fetchall()

                    scores = [float(s[1]) for s in sessions]
                    c3.metric(
                        "Average Score",
                        f"{(sum(scores) / len(scores)) if scores else 0:.1f}"
                    )
                    st.metric(
                        "Best Score",
                        f"{max(scores) if scores else 0:.1f}"
                    )

                    st.write(f"**Phone:** {patient_data[6]}")
                    st.write(f"**Email:** {patient_data[7]}")
                    st.write(f"**Location:** {patient_data[8]}")

                    if sessions:
                        st.dataframe(
                            [
                                {
                                    "Game": s[0],
                                    "Score": s[1],
                                    "Difficulty": s[2],
                                    "Date": s[3]
                                }
                                for s in sessions
                            ],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("No game sessions recorded.")

    with caretaker_tabs[4]:

        if own_patients:
            patient_map = {
                f"{p[1]} ({p[2]})": p[0]
                for p in own_patients
            }
            selected_reminder_patient = st.selectbox(
                "Select Patient",
                list(patient_map.keys()),
                key="caretaker_reminder_patient"
            )
            reminder_patient_id = patient_map[selected_reminder_patient]

            if provider_can_manage_patient(
                user_id,
                "caretaker",
                reminder_patient_id
            ):
                patient_reminders = conn.execute(
                    """
                    SELECT id, title, due_time, status
                    FROM reminders
                    WHERE user_id=?
                    ORDER BY id DESC
                    """,
                    (reminder_patient_id,)
                ).fetchall()

                if patient_reminders:
                    st.dataframe(
                        [
                            {
                                "Reminder": r[1],
                                "Due": r[2],
                                "Status": r[3]
                            }
                            for r in patient_reminders
                        ],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No reminders recorded for this patient.")

    with caretaker_tabs[5]:

        st.write(f"**Phone:** {caretaker_profile[0] if caretaker_profile else ''}")
        st.write(f"**Email:** {caretaker_profile[1] if caretaker_profile else ''}")
        st.write(f"**Location:** {caretaker_profile[2] if caretaker_profile else ''}")
        st.write(f"**Care Role:** {caretaker_profile[3] if caretaker_profile else ''}")
        st.write(f"**Account Status:** {caretaker_profile[4] if caretaker_profile else ''}")

    st.divider()

    if st.button(
        "🚪 Logout",
        key="caretaker_logout"
    ):
        st.session_state.clear()
        st.rerun()

    st.stop()


# ============================================================
# LOAD PATIENT
# ============================================================

patient = conn.execute(
    """
    SELECT
        id,
        name,
        username,
        language,
        baseline,
        role,
        doctor_id,
        adaptive_difficulty,
        caretaker_id,
        phone,
        email,
        location
    FROM users
    WHERE id=?
    AND role='patient'
    """,
    (
        user_id,
    )
).fetchone()


if patient is None:

    st.error(
        "Patient account could not be loaded."
    )

    st.session_state.clear()

    st.stop()


# ============================================================
# REFRESH PATIENT INFORMATION
# ============================================================

user_id = patient[0]
name = patient[1]
username = patient[2]
language = patient[3]
doctor_id = patient[6]
caretaker_id = patient[8] if len(patient) > 8 else None
phone = patient[9] if len(patient) > 9 else ""
email = patient[10] if len(patient) > 10 else ""
location = patient[11] if len(patient) > 11 else ""
st.session_state.caretaker_id = caretaker_id


# ============================================================
# BASELINE
# ============================================================

def calculate_baseline(
    patient_id
):

    rows = conn.execute(
        """
        SELECT score
        FROM sessions
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (
            patient_id,
        )
    ).fetchall()

    if not rows:

        return 0.0

    return round(
        sum(
            float(row[0])
            for row in rows
        ) / len(rows),
        1
    )


baseline = calculate_baseline(
    user_id
)


# ============================================================
# GET CURRENT DIFFICULTY
# ============================================================

difficulty_row = conn.execute(
    """
    SELECT adaptive_difficulty
    FROM users
    WHERE id=?
    AND role='patient'
    """,
    (
        user_id,
    )
).fetchone()


if difficulty_row:

    difficulty = int(
        difficulty_row[0] or 1
    )

else:

    difficulty = 1


difficulty = max(
    1,
    min(
        difficulty,
        3
    )
)


# ============================================================
# UPDATE DIFFICULTY
# ============================================================

def update_adaptive_difficulty(
    patient_id,
    score
):

    row = conn.execute(
        """
        SELECT adaptive_difficulty
        FROM users
        WHERE id=?
        AND role='patient'
        """,
        (
            patient_id,
        )
    ).fetchone()

    if row:

        old_difficulty = int(
            row[0] or 1
        )

    else:

        old_difficulty = 1

    # --------------------------------------------------------
    # STRONG PERFORMANCE
    # --------------------------------------------------------

    if score >= 70:

        new_difficulty = min(
            old_difficulty + 1,
            3
        )

        result = "won"

    # --------------------------------------------------------
    # WEAK PERFORMANCE
    # --------------------------------------------------------

    else:

        new_difficulty = max(
            old_difficulty - 1,
            1
        )

        result = "lost"

    conn.execute(
        """
        UPDATE users
        SET adaptive_difficulty=?
        WHERE id=?
        AND role='patient'
        """,
        (
            new_difficulty,
            patient_id
        )
    )

    conn.commit()

    return (
        old_difficulty,
        new_difficulty,
        result
    )


# ============================================================
# GAME COMPLETION VOICE
# ============================================================

def game_result_voice(
    game_name,
    score,
    old_difficulty,
    new_difficulty,
    language
):

    if score >= 70:

        message = (
            f"Congratulations! "
            f"You completed the {game_name} "
            f"with a score of {score}. "
        )

        if new_difficulty > old_difficulty:

            message += (
                f"Excellent performance. "
                f"Your difficulty has increased "
                f"to level {new_difficulty}."
            )

        else:

            message += (
                f"Your difficulty remains at "
                f"level {new_difficulty}."
            )

    else:

        message = (
            f"You completed the {game_name} "
            f"with a score of {score}. "
        )

        if new_difficulty < old_difficulty:

            message += (
                f"Keep practicing. "
                f"Your difficulty has been adjusted "
                f"to level {new_difficulty}."
            )

        else:

            message += (
                f"Your difficulty remains at "
                f"level {new_difficulty}."
            )

    return message


# ============================================================
# VOICE COMMAND HELPERS
# ============================================================
VOICE_ALIASES = {
    "logout": ["logout", "log out", "exit", "sign out", "लॉगआउट", "लॉग आउट", "выйти", "выход"],
    "games": ["game", "games", "play", "cognitive", "cognitive game", "खेल", "गेम", "खेळ", "игра", "игры"],
    "reminders": ["reminder", "reminders", "set reminder", "add reminder", "remind me", "रिमाइंडर", "स्मरणपत्र", "напоминание", "напоминания"],
    "reports": ["report", "reports", "open report", "open reports", "रिपोर्ट", "अहवाल", "отчёт", "отчет", "отчеты"],
    "history": ["history", "performance", "my history", "मेरा इतिहास", "इतिहास", "माझा इतिहास", "история"],
    "details": ["details", "profile", "my data", "my details", "मेरी जानकारी", "माहिती", "мои данные", "профиль"],
    "home": ["home", "dashboard", "go home", "main page", "होम", "मुख्यपृष्ठ", "домой", "главная"]
}

def clean_voice_command(command):
    if not command:
        return ""
    command = command.lower().strip()
    command = re.sub(r"[^\w\s:/.-]", " ", command, flags=re.UNICODE)
    return re.sub(r"\s+", " ", command).strip()

def command_matches(command, action):
    command = clean_voice_command(command)
    return any(command == alias or alias in command for alias in VOICE_ALIASES.get(action, []))


# ============================================================
# PATIENT SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## 🧠 MINDSETU NER"
    )

    st.write(
        f"👤 **{name}**"
    )

    st.caption(
        "Role: Patient"
    )

    st.divider()

    # ========================================================
    # LANGUAGE
    # ========================================================

    st.subheader(
        "🌐 " +
        text(
            "language",
            language
        )
    )

    language_options = list(
        LANGUAGES.keys()
    )

    current_index = (
        language_options.index(language)
        if language in language_options
        else 0
    )

    selected_language = st.selectbox(
        "Select Language",
        language_options,
        index=current_index,
        key="patient_language_select"
    )

    if selected_language != language:

        conn.execute(
            """
            UPDATE users
            SET language=?
            WHERE id=?
            AND role='patient'
            """,
            (
                selected_language,
                user_id
            )
        )

        conn.commit()

        st.session_state.language = (
            selected_language
        )

        queue_voice(
            (
                "Language changed to "
                f"{selected_language} successfully."
            ),
            selected_language
        )

        st.rerun()

    # ========================================================
    # VOICE COMMANDS
    # ========================================================

    st.divider()

    st.subheader(
        "🎤 Voice"
    )

    if mic_recorder is None:

        st.warning(
            "Voice input package is not installed."
        )

    else:

        st.caption("Click 🎤, speak clearly, then click ⏹️ to stop.")

        audio_data = mic_recorder(
            start_prompt="🎤 Start Listening",
            stop_prompt="⏹️ Stop Listening",
            just_once=True,
            key="patient_voice_recorder"
        )

        if audio_data:

            command, voice_error = recognize_voice(
                audio_data["bytes"],
                language
            )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # We NEVER display:
            #
            # st.success(command)
            #
            # Therefore the user's speech is not shown.
            # ------------------------------------------------

            if command:

                st.caption(f'🎤 I heard: "{command}"')
                command = clean_voice_command(command)

                # =================================================
                # LOGOUT
                # =================================================

                if command_matches(command, "logout"):

                    queue_voice(
                        "Logging out now.",
                        language
                    )

                    st.session_state.logged_in = False

                    st.rerun()

                # =================================================
                # GAMES
                # =================================================

                elif command_matches(command, "games"):

                    st.session_state.page = "games"

                    queue_voice(
                        (
                            "Opening cognitive games. "
                            "You can start a game whenever you are ready."
                        ),
                        language
                    )

                    st.rerun()

                # =================================================
                # REMINDERS
                # =================================================

                elif command_matches(command, "reminders") or "set time" in command or "set a time" in command:

                    reminder_time = (
                        parse_time_from_command(
                            command
                        )
                    )

                    if reminder_time:

                        reminder_title = (
                            extract_reminder_title(
                                command
                            )
                        )

                        conn.execute(
                            """
                            INSERT INTO reminders(
                                user_id,
                                title,
                                due_time,
                                status
                            )
                            VALUES(
                                ?,
                                ?,
                                ?,
                                'Pending'
                            )
                            """,
                            (
                                user_id,
                                reminder_title,
                                (
                                    f"{date.today()} "
                                    f"{reminder_time}"
                                )
                            )
                        )

                        conn.commit()

                        queue_voice(
                            (
                                f"{reminder_title} "
                                f"reminder has been added "
                                f"for {reminder_time}."
                            ),
                            language
                        )

                    else:

                        queue_voice(
                            (
                                "I heard the reminder request, "
                                "but I could not understand the time. "
                                "Please say something like "
                                "set reminder drink water at 5 PM."
                            ),
                            language
                        )

                    st.session_state.page = "reminders"

                    st.rerun()

                # =================================================
                # REPORTS
                # =================================================

                elif command_matches(command, "reports"):

                    st.session_state.page = "reports"

                    queue_voice(
                        "Opening your reports.",
                        language
                    )

                    st.rerun()

                # =================================================
                # HISTORY
                # =================================================

                elif command_matches(command, "history"):

                    st.session_state.page = "history"

                    queue_voice(
                        "Opening your performance history.",
                        language
                    )

                    st.rerun()

                # =================================================
                # DETAILS
                # =================================================

                elif command_matches(command, "details"):

                    st.session_state.page = "details"

                    queue_voice(
                        "Opening your details.",
                        language
                    )

                    st.rerun()

                # =================================================
                # HOME
                # =================================================

                elif command_matches(command, "home"):

                    st.session_state.page = "home"

                    queue_voice(
                        "Opening your dashboard.",
                        language
                    )

                    st.rerun()

                # =================================================
                # UNKNOWN COMMAND
                # =================================================

                else:

                    queue_voice(
                        (
                            "Sorry, I did not understand "
                            "that command. "
                            "You can say open games, "
                            "open reminders, "
                            "open reports, "
                            "open history, "
                            "open details, "
                            "go home, "
                            "or logout."
                        ),
                        language
                    )

                    st.rerun()

            else:

                if voice_error:
                    st.warning(f"🎤 {voice_error}")

                queue_voice(
                    (
                        "Sorry, I could not understand "
                        "your voice. Please try again."
                    ),
                    language
                )

                st.rerun()

    st.divider()

    # ========================================================
    # LOGOUT BUTTON
    # ========================================================

    if st.button(
        "🚪 " +
        text(
            "logout",
            language
        ),
        use_container_width=True
    ):

        queue_voice(
            "Logging out now. Goodbye.",
            language
        )

        st.session_state.logged_in = False

        st.rerun()


# ============================================================
# PATIENT NAVIGATION
# ============================================================

page_names = {

    "home":
        "🏠 " +
        text(
            "home",
            language
        ),

    "games":
        "🎮 " +
        text(
            "games",
            language
        ),

    "reminders":
        "⏰ " +
        text(
            "reminders",
            language
        ),

    "history":
        "📜 " +
        text(
            "history",
            language
        ),

    "details":
        "👤 " +
        text(
            "details",
            language
        ),

    "reports":
        "📄 " +
        text(
            "reports",
            language
        )
}


page_keys = list(
    page_names.keys()
)


current_page = st.session_state.page


if current_page not in page_keys:

    current_page = "home"


selected_page = st.radio(
    "Navigation",
    page_keys,
    format_func=lambda key: page_names[key],
    horizontal=True,
    index=page_keys.index(
        current_page
    )
)


st.session_state.page = selected_page


# ============================================================
# MULTI-ROUND GAME SETTINGS
# ============================================================

GAME_ROUNDS_BY_DIFFICULTY = {
    1: 15,
    2: 18,
    3: 20,
}


def reset_memory_game():
    st.session_state.memory_sequence = None
    st.session_state.memory_round = 0
    st.session_state.memory_total_score = 0.0
    st.session_state.memory_start_time = None
    st.session_state.memory_answer_phase = False


def reset_pattern_game():
    st.session_state.pattern_sequence = None
    st.session_state.pattern_round = 0
    st.session_state.pattern_total_score = 0.0


def reset_attention_game():
    st.session_state.reaction_target = None
    st.session_state.attention_round = 0
    st.session_state.attention_total_score = 0.0


def reset_image_memory_game():
    """Reset all state for the patient-only Image Recognition game."""
    st.session_state.image_memory_round = 0
    st.session_state.image_memory_total_score = 0.0
    st.session_state.image_memory_sequence = []
    st.session_state.image_memory_choices = []
    st.session_state.image_memory_start_time = None
    st.session_state.image_memory_answer_phase = False
    st.session_state.image_memory_selected = []


def exit_current_game(game_name):
    if game_name == "Memory Sequence":
        reset_memory_game()
    elif game_name == "Pattern Memory":
        reset_pattern_game()
    elif game_name == "Attention Game":
        reset_attention_game()
    elif game_name == "Image Recognition":
        reset_image_memory_game()

    queue_voice(
        f"You exited the {game_name}. The unfinished game was not saved.",
        language
    )
    st.rerun()


def save_completed_game(game_name, final_score):
    conn.execute(
        """
        INSERT INTO sessions(
            user_id, game, score, difficulty, created_at
        )
        VALUES(?, ?, ?, ?, ?)
        """,
        (
            user_id,
            game_name,
            round(float(final_score), 1),
            difficulty,
            datetime.now().isoformat(timespec="seconds")
        )
    )
    conn.commit()


# ============================================================
# IMAGE RECOGNITION GAME ASSETS
# ============================================================
#
# The image game is fully self-contained: it does not require an external
# image directory or another Python package. Each image card is represented
# by a clean visual card containing an image-like emoji illustration.
#
# The game randomly chooses a target set, displays those image cards for
# exactly 10 seconds, hides them at 0 seconds, and only then activates the
# answer choices. A one-second Streamlit autorefresh keeps the countdown and
# phase transition synchronized without blocking the application.
# ============================================================

IMAGE_GAME_ITEMS = {
    "apple": {"label": "Apple", "emoji": "🍎", "bg": "#FFE4E6"},
    "book": {"label": "Book", "emoji": "📚", "bg": "#E0F2FE"},
    "car": {"label": "Car", "emoji": "🚗", "bg": "#FEF3C7"},
    "dog": {"label": "Dog", "emoji": "🐶", "bg": "#DCFCE7"},
    "flower": {"label": "Flower", "emoji": "🌸", "bg": "#FCE7F3"},
    "house": {"label": "House", "emoji": "🏠", "bg": "#EDE9FE"},
    "moon": {"label": "Moon", "emoji": "🌙", "bg": "#E0E7FF"},
    "parrot": {"label": "Parrot", "emoji": "🦜", "bg": "#CCFBF1"},
    "pencil": {"label": "Pencil", "emoji": "✏️", "bg": "#FEF9C3"},
    "phone": {"label": "Phone", "emoji": "📱", "bg": "#E2E8F0"},
    "sun": {"label": "Sun", "emoji": "☀️", "bg": "#FFEDD5"},
    "tree": {"label": "Tree", "emoji": "🌳", "bg": "#D1FAE5"},
    "umbrella": {"label": "Umbrella", "emoji": "☂️", "bg": "#DBEAFE"},
    "watch": {"label": "Watch", "emoji": "⌚", "bg": "#F1F5F9"},
    "ball": {"label": "Ball", "emoji": "⚽", "bg": "#E5E7EB"},
    "camera": {"label": "Camera", "emoji": "📷", "bg": "#F3F4F6"},
}

IMAGE_GAME_DIFFICULTY = {
    1: {"target_count": 4, "choice_count": 8},
    2: {"target_count": 6, "choice_count": 10},
    3: {"target_count": 8, "choice_count": 12},
}


def image_card_html(item_key, compact=False):
    """Return a clear image-like card for the image memory game."""
    item = IMAGE_GAME_ITEMS[item_key]
    width = 105 if compact else 140
    height = 125 if compact else 150
    emoji_size = 48 if compact else 64
    label_size = 12 if compact else 15

    return f"""
    <div style="
        width:{width}px;
        min-height:{height}px;
        border-radius:18px;
        padding:10px;
        box-sizing:border-box;
        background:{item['bg']};
        border:2px solid rgba(79,70,229,.18);
        display:flex;
        flex-direction:column;
        justify-content:center;
        align-items:center;
        box-shadow:0 6px 18px rgba(15,23,42,.10);
        margin:auto;
    ">
        <div style="font-size:{emoji_size}px;line-height:1.1;">{item['emoji']}</div>
        <div style="margin-top:8px;font-weight:800;font-size:{label_size}px;color:#1E293B;text-align:center;">
            {item['label']}
        </div>
    </div>
    """


def render_image_cards(item_keys, compact=False):
    """Render image cards in a centered responsive flex container."""
    cards = "".join(
        image_card_html(key, compact=compact)
        for key in item_keys
    )

    return f"""
    <div style="
        display:flex;
        flex-wrap:wrap;
        justify-content:center;
        align-items:center;
        gap:14px;
        width:100%;
        padding:8px 0;
    ">
        {cards}
    </div>
    """


def image_countdown_banner(seconds_remaining):
    """Return a large, readable countdown badge."""
    if seconds_remaining <= 0:
        return """
        <div style="
            display:block;
            width:max-content;
            margin:8px auto;
            padding:10px 20px;
            border-radius:999px;
            background:#DCFCE7;
            color:#166534;
            font-weight:900;
            font-size:18px;
            border:2px solid #86EFAC;
        ">
            ✅ 0 seconds - images hidden
        </div>
        """

    return f"""
    <div style="
        display:block;
        width:max-content;
        min-width:130px;
        margin:8px auto;
        padding:10px 22px;
        border-radius:999px;
        background:#3730A3;
        color:white;
        font-weight:900;
        text-align:center;
        font-size:21px;
        border:2px solid #818CF8;
        box-shadow:0 5px 18px rgba(55,48,163,.25);
    ">
        ⏱️ {seconds_remaining} seconds
    </div>
    """


def image_remaining_seconds():
    """Calculate remaining 10-second viewing time without time.sleep()."""
    start = st.session_state.get("image_memory_start_time")

    if start is None:
        return 0

    elapsed = pytime.time() - float(start)
    return max(0, 10 - int(elapsed))


def prepare_image_memory_round(difficulty_level, round_number):
    """Create a target image set and distractor choices for a new round."""
    config = IMAGE_GAME_DIFFICULTY[difficulty_level]
    all_keys = list(IMAGE_GAME_ITEMS.keys())

    target_keys = random.sample(
        all_keys,
        config["target_count"]
    )

    remaining_keys = [
        key
        for key in all_keys
        if key not in target_keys
    ]

    distractor_count = (
        config["choice_count"]
        - config["target_count"]
    )

    distractors = random.sample(
        remaining_keys,
        distractor_count
    )

    answer_choices = target_keys + distractors
    random.shuffle(answer_choices)

    st.session_state.image_memory_sequence = target_keys
    st.session_state.image_memory_choices = answer_choices
    st.session_state.image_memory_round = round_number
    st.session_state.image_memory_total_score = (
        st.session_state.get("image_memory_total_score", 0.0)
    )
    st.session_state.image_memory_start_time = pytime.time()
    st.session_state.image_memory_answer_phase = False
    st.session_state.image_memory_selected = []


def save_image_game_result(final_score, old_difficulty, new_difficulty):
    """Save a completed image game and populate the common result banner."""
    rounded_score = round(float(final_score), 1)

    save_completed_game(
        "Image Recognition",
        rounded_score
    )

    st.session_state.game_result_message = game_result_voice(
        "Image Recognition Game",
        rounded_score,
        old_difficulty,
        new_difficulty,
        language
    )
    st.session_state.game_result_score = rounded_score
    st.session_state.game_result_old_difficulty = old_difficulty
    st.session_state.game_result_new_difficulty = new_difficulty


# ============================================================
# PATIENT HOME
# ============================================================

if selected_page == "home":
    # Use textwrap.dedent so the HTML is rendered as HTML,
    # instead of being displayed as a code block.
    home_html = textwrap.dedent(
        f"""
        <div style="
            padding:25px;
            border-radius:20px;
            background:linear-gradient(
                135deg,
                #667eea,
                #764ba2
            );
            color:white;
        ">
            <h1>
                🧠 {text("welcome", language)}, {name}!
            </h1>

         </div>
        """
    )

    st.markdown(
        home_html,
        unsafe_allow_html=True
    )

    st.write("")

    total_sessions = conn.execute(
        """
        SELECT COUNT(*)
        FROM sessions
        WHERE user_id=?
        """,
        (
            user_id,
        )
    ).fetchone()[0]

    report_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM reports
        WHERE patient_id=?
        """,
        (
            user_id,
        )
    ).fetchone()[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Personal Baseline",
        f"{baseline:.1f}"
    )

    c2.metric(
        "Difficulty",
        difficulty
    )

    c3.metric(
        "Sessions",
        total_sessions
    )

    c4.metric(
        "Reports",
        report_count
    )

    st.divider()

    if doctor_id:

        doctor = conn.execute(
            """
            SELECT name, username, phone, email, location
            FROM users
            WHERE id=?
            AND role='doctor'
            """,
            (doctor_id,)
        ).fetchone()

        if doctor:
            st.success(
                f"🩺 Assigned Doctor: Dr. {doctor[0]}"
            )
            st.caption(
                f"Phone: {doctor[2]} | Email: {doctor[3]} | Location: {doctor[4]}"
            )

    elif caretaker_id:

        caretaker = conn.execute(
            """
            SELECT name, username, phone, email, location
            FROM users
            WHERE id=?
            AND role='caretaker'
            """,
            (caretaker_id,)
        ).fetchone()

        if caretaker:
            st.success(
                f"🤝 Assigned Caretaker: {caretaker[0]}"
            )
            st.caption(
                f"Phone: {caretaker[2]} | Email: {caretaker[3]} | Location: {caretaker[4]}"
            )

    else:

        st.info(
            "🩺/🤝 No doctor or caretaker has been linked yet. "
            "A local doctor or caretaker can add you directly from their portal."
        )

    st.info(
        "Your game difficulty adapts after every "
        "completed game. Strong performance increases "
        "the difficulty; weaker performance decreases it."
    )


# ============================================================
# COGNITIVE GAMES
# ============================================================

elif selected_page == "games":

    # Show the most recent completed-game result once after returning
    # from the completed multi-round game.
    if st.session_state.get("game_result_message"):
        completed_score = st.session_state.get("game_result_score")
        old_level = st.session_state.get("game_result_old_difficulty")
        new_level = st.session_state.get("game_result_new_difficulty")

        if completed_score is not None and completed_score >= 70:
            st.success(
                f"🎉 Congratulations! You completed the game with a score of "
                f"{completed_score:.1f}/100."
            )

            if new_level is not None and old_level is not None and new_level > old_level:
                st.success(
                    f"⬆️ Excellent performance! Your difficulty level increased "
                    f"from {old_level} to {new_level}."
                )
            else:
                st.info(
                    f"⭐ Your current difficulty level is {new_level}."
                )
        else:
            st.info(
                f"Game completed with a score of {completed_score:.1f}/100. "
                f"Keep practicing! Your current difficulty level is {new_level}."
            )

        # Keep the message from repeating on every later games-page visit.
        st.session_state.game_result_message = None
        st.session_state.game_result_score = None
        st.session_state.game_result_old_difficulty = None
        st.session_state.game_result_new_difficulty = None

    st.title(
        "🎮 " +
        text(
            "games",
            language
        )
    )

    st.write(
        f"Adaptive difficulty level: **{difficulty} / 3**"
    )

    total_rounds = GAME_ROUNDS_BY_DIFFICULTY[difficulty]

    st.info(
        f"This game contains {total_rounds} rounds at the current difficulty. "
        "You can exit an unfinished game at any time. "
        "Strong performance (70 or above) increases the difficulty level; "
        "lower performance decreases it."
    )

    # Streamlit tabs return to the first tab after every rerun. Since the
    # games intentionally rerun for timers, answers and next rounds, tabs
    # can make an active game look like it returned to "Start Game". Use a
    # persistent game selector instead. The selected game survives every
    # rerun and each game keeps its own session state.
    if "active_game" not in st.session_state:
        st.session_state.active_game = "Memory Sequence"

    active_game = st.radio(
        "Choose Game",
        [
            "Memory Sequence",
            "Pattern Memory",
            "Attention Game",
            "Image Recognition"
        ],
        key="active_game",
        horizontal=True,
        format_func=lambda x: {
            "Memory Sequence": "🧠 Memory Sequence",
            "Pattern Memory": "🔷 Pattern Memory",
            "Attention Game": "⚡ Attention Game",
            "Image Recognition": "🖼️ Image Recognition"
        }[x]
    )

    st.divider()

    # ========================================================
    # MEMORY SEQUENCE
    # ========================================================

    if active_game == "Memory Sequence":

        st.subheader("🧠 Memory Sequence")

        sequence_length = {
            1: 4,
            2: 6,
            3: 8
        }[difficulty]

        if st.session_state.memory_round == 0:

            st.write(
                f"You will play {total_rounds} rounds. "
                f"Remember {sequence_length} numbers in each round."
            )

            if st.button(
                "▶️ Start Memory Game",
                type="primary",
                key="memory_start"
            ):

                st.session_state.memory_round = 1
                st.session_state.memory_total_score = 0.0
                st.session_state.memory_sequence = random.sample(
                    range(1, 10),
                    sequence_length
                )
                st.session_state.memory_start_time = pytime.time()
                st.session_state.memory_answer_phase = False

                queue_voice(
                    f"Memory game started. Round 1 of {total_rounds}. "
                    f"You have 10 seconds to remember {sequence_length} numbers. "
                    "The numbers will then disappear. Enter the sequence from memory.",
                    language
                )

                st.rerun()

        else:

            current_round = st.session_state.memory_round
            sequence = st.session_state.memory_sequence

            st.progress(
                current_round / total_rounds,
                text=f"Round {current_round} of {total_rounds}"
            )

            # --------------------------------------------------------
            # 10-SECOND MEMORY DISPLAY / ANSWER LOCK
            # --------------------------------------------------------
            # The timer is stored in session_state so every Streamlit rerun
            # continues the SAME round instead of starting it again.
            if not st.session_state.get("memory_answer_phase", False):
                if st.session_state.get("memory_start_time") is None:
                    st.session_state.memory_start_time = pytime.time()

                elapsed = pytime.time() - float(st.session_state.memory_start_time)
                remaining = max(0, 10 - int(elapsed))

                # IMPORTANT: create the text before displaying it.
                sequence_text = "   •   ".join(str(number) for number in sequence)

                # Use normal Streamlit rendering so the numbers are clearly
                # visible in every browser/theme.
                st.markdown(
                    "<div style=\"text-align:center; font-size:20px; font-weight:700; margin-top:15px;\">"
                    "🧠 MEMORIZE THESE NUMBERS"
                    "</div>",
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"<div style=\"background:#EEF2FF; border:3px solid #4F46E5; "
                    f"border-radius:18px; padding:28px 12px; text-align:center; "
                    f"margin:12px 0;\">"
                    f"<div style=\"font-size:42px; font-weight:900; "
                    f"letter-spacing:6px; color:#111827;\">{sequence_text}</div>"
                    f"<div style=\"font-size:30px; font-weight:900; "
                    f"margin-top:18px; color:#B91C1C;\">⏱️ {remaining}</div>"
                    f"<div style=\"font-size:15px; margin-top:8px; color:#374151;\">"
                    f"Numbers disappear at 0 seconds</div></div>",
                    unsafe_allow_html=True
                )

                st.info(
                    f"🔒 Answer locked — memorize the numbers. "
                    f"Time remaining: **{remaining} seconds**"
                )

                if remaining > 0:
                    if st_autorefresh is not None:
                        st_autorefresh(
                            interval=250,
                            limit=50,
                            key=f"memory_timer_{user_id}_{current_round}"
                        )
                    else:
                        st.warning(
                            "Please add **streamlit-autorefresh** to requirements.txt "
                            "for the live countdown."
                        )
                else:
                    # Switch permanently to answer phase. Do NOT clear
                    # memory_start_time, otherwise the next rerun would
                    # accidentally restart the 10-second timer.
                    st.session_state.memory_answer_phase = True
                    st.rerun()

            else:
                # --------------------------------------------------------
                # ANSWER PHASE — numbers are hidden and input is enabled
                # --------------------------------------------------------
                st.markdown(
                    "<div style=\"text-align:center; padding:22px; "
                    "border:3px solid #16A34A; border-radius:18px; "
                    "background:#F0FDF4; margin:12px 0;\">"
                    "<div style=\"font-size:30px; font-weight:900; color:#15803D;\">"
                    "⏱️ 0 — NUMBERS DISAPPEARED</div>"
                    "<div style=\"font-size:18px; margin-top:8px;\">"
                    "Now enter the numbers in the same order.</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
                st.success("✅ Answer box is now active!")
            answer = st.text_input(
                "Enter the numbers in the same order",
                key=f"memory_answer_{current_round}",
                disabled=not st.session_state.get("memory_answer_phase", False)
            )

            exit_col, submit_col = st.columns(2)

            with exit_col:

                if st.button(
                    "🚪 Exit Game",
                    key=f"memory_exit_{current_round}",
                    use_container_width=True
                ):
                    exit_current_game("Memory Sequence")

            with submit_col:

                if st.button(
                    "Submit Round",
                    key=f"memory_submit_{current_round}",
                    type="primary",
                    use_container_width=True
                ):

                    try:

                        user_answer = [
                            int(x)
                            for x in re.split(
                                r"[,\s]+",
                                answer.strip()
                            )
                            if x
                        ]

                        if len(user_answer) != len(sequence):

                            st.error(
                                f"Enter exactly {len(sequence)} numbers."
                            )

                        else:

                            correct = sum(
                                a == b
                                for a, b in zip(
                                    sequence,
                                    user_answer
                                )
                            )

                            round_score = (
                                correct /
                                len(sequence)
                            ) * 100

                            st.session_state.memory_total_score += round_score

                            if current_round >= total_rounds:

                                final_score = (
                                    st.session_state.memory_total_score /
                                    total_rounds
                                )

                                save_completed_game(
                                    "Memory Sequence",
                                    final_score
                                )

                                old_difficulty, new_difficulty, result = (
                                    update_adaptive_difficulty(
                                        user_id,
                                        final_score
                                    )
                                )

                                st.session_state.game_result_message = game_result_voice(
                                    "Memory Game",
                                    round(final_score, 1),
                                    old_difficulty,
                                    new_difficulty,
                                    language
                                )
                                st.session_state.game_result_score = round(final_score, 1)
                                st.session_state.game_result_old_difficulty = old_difficulty
                                st.session_state.game_result_new_difficulty = new_difficulty

                                reset_memory_game()

                                queue_voice(
                                    game_result_voice(
                                        "Memory Game",
                                        round(final_score, 1),
                                        old_difficulty,
                                        new_difficulty,
                                        language
                                    ),
                                    language
                                )

                                st.rerun()

                            else:

                                next_round = current_round + 1
                                st.session_state.memory_round = next_round
                                st.session_state.memory_sequence = random.sample(
                                    range(1, 10),
                                    sequence_length
                                )
                                st.session_state.memory_start_time = pytime.time()
                                st.session_state.memory_answer_phase = False

                                st.rerun()

                    except ValueError:

                        st.error(
                            "Please enter numbers only."
                        )

    # ========================================================
    # PATTERN MEMORY
    # ========================================================

    if active_game == "Pattern Memory":

        st.subheader("🔷 Pattern Memory")

        pattern_length = {
            1: 4,
            2: 6,
            3: 8
        }[difficulty]

        symbols = [
            "▲",
            "●",
            "■",
            "◆"
        ]

        if st.session_state.pattern_round == 0:

            st.write(
                f"You will play {total_rounds} rounds. "
                f"Remember {pattern_length} symbols in each round."
            )

            if st.button(
                "▶️ Start Pattern Game",
                type="primary",
                key="pattern_start"
            ):

                st.session_state.pattern_round = 1
                st.session_state.pattern_total_score = 0.0
                st.session_state.pattern_sequence = [
                    random.choice(symbols)
                    for _ in range(pattern_length)
                ]

                queue_voice(
                    f"Pattern game started. Round 1 of {total_rounds}. "
                    f"Remember {pattern_length} symbols.",
                    language
                )

                st.rerun()

        else:

            current_round = st.session_state.pattern_round
            pattern = st.session_state.pattern_sequence

            st.progress(
                current_round / total_rounds,
                text=f"Round {current_round} of {total_rounds}"
            )

            st.success("Remember this pattern:")

            st.markdown(
                "## " +
                " ".join(pattern)
            )

            pattern_answer = st.text_input(
                "Enter the pattern using symbols",
                placeholder="Example: ▲ ● ■ ◆",
                key=f"pattern_answer_{current_round}"
            )

            exit_col, submit_col = st.columns(2)

            with exit_col:

                if st.button(
                    "🚪 Exit Game",
                    key=f"pattern_exit_{current_round}",
                    use_container_width=True
                ):
                    exit_current_game("Pattern Memory")

            with submit_col:

                if st.button(
                    "Submit Round",
                    key=f"pattern_submit_{current_round}",
                    type="primary",
                    use_container_width=True
                ):

                    answer_symbols = (
                        pattern_answer
                        .strip()
                        .split()
                    )

                    if len(answer_symbols) != len(pattern):

                        st.error(
                            f"Enter exactly {len(pattern)} symbols."
                        )

                    else:

                        correct = sum(
                            a == b
                            for a, b in zip(
                                pattern,
                                answer_symbols
                            )
                        )

                        round_score = (
                            correct /
                            len(pattern)
                        ) * 100

                        st.session_state.pattern_total_score += round_score

                        if current_round >= total_rounds:

                            final_score = (
                                st.session_state.pattern_total_score /
                                total_rounds
                            )

                            save_completed_game(
                                "Pattern Memory",
                                final_score
                            )

                            old_difficulty, new_difficulty, result = (
                                update_adaptive_difficulty(
                                    user_id,
                                    final_score
                                )
                            )

                            st.session_state.game_result_message = game_result_voice(
                                "Pattern Memory Game",
                                round(final_score, 1),
                                old_difficulty,
                                new_difficulty,
                                language
                            )
                            st.session_state.game_result_score = round(final_score, 1)
                            st.session_state.game_result_old_difficulty = old_difficulty
                            st.session_state.game_result_new_difficulty = new_difficulty

                            reset_pattern_game()

                            queue_voice(
                                game_result_voice(
                                    "Pattern Memory Game",
                                    round(final_score, 1),
                                    old_difficulty,
                                    new_difficulty,
                                    language
                                ),
                                language
                            )

                            st.rerun()

                        else:

                            next_round = current_round + 1
                            st.session_state.pattern_round = next_round
                            st.session_state.pattern_sequence = [
                                random.choice(symbols)
                                for _ in range(pattern_length)
                            ]

                            st.rerun()

    # ========================================================
    # ATTENTION GAME
    # ========================================================

    if active_game == "Attention Game":

        st.subheader("⚡ Attention Game")

        st.write(
            "Click the target number."
        )

        if st.session_state.attention_round == 0:

            st.write(
                f"You will play {total_rounds} rounds. "
                "Find the target number in each round."
            )

            if st.button(
                "▶️ Start Attention Game",
                type="primary",
                key="attention_start"
            ):

                st.session_state.attention_round = 1
                st.session_state.attention_total_score = 0.0
                st.session_state.reaction_target = random.randint(1, 9)

                queue_voice(
                    f"Attention game started. Round 1 of {total_rounds}. "
                    "Find the target number.",
                    language
                )

                st.rerun()

        else:

            current_round = st.session_state.attention_round
            target = st.session_state.reaction_target

            st.progress(
                current_round / total_rounds,
                text=f"Round {current_round} of {total_rounds}"
            )

            st.markdown(
                f"## Find: **{target}**"
            )

            if st.button(
                "🚪 Exit Game",
                key=f"attention_exit_{current_round}",
                use_container_width=True
            ):
                exit_current_game("Attention Game")

            cols = st.columns(3)
            numbers = list(range(1, 10))
            random.shuffle(numbers)

            for index, number in enumerate(numbers):

                with cols[index % 3]:

                    if st.button(
                        str(number),
                        key=f"attention_{current_round}_{number}"
                    ):

                        round_score = (
                            100
                            if number == target
                            else 0
                        )

                        st.session_state.attention_total_score += round_score

                        if current_round >= total_rounds:

                            final_score = (
                                st.session_state.attention_total_score /
                                total_rounds
                            )

                            save_completed_game(
                                "Attention Game",
                                final_score
                            )

                            old_difficulty, new_difficulty, result = (
                                update_adaptive_difficulty(
                                    user_id,
                                    final_score
                                )
                            )

                            st.session_state.game_result_message = game_result_voice(
                                "Attention Game",
                                round(final_score, 1),
                                old_difficulty,
                                new_difficulty,
                                language
                            )
                            st.session_state.game_result_score = round(final_score, 1)
                            st.session_state.game_result_old_difficulty = old_difficulty
                            st.session_state.game_result_new_difficulty = new_difficulty

                            reset_attention_game()

                            queue_voice(
                                game_result_voice(
                                    "Attention Game",
                                    round(final_score, 1),
                                    old_difficulty,
                                    new_difficulty,
                                    language
                                ),
                                language
                            )

                            st.rerun()

                        else:

                            st.session_state.attention_round = current_round + 1
                            st.session_state.reaction_target = random.randint(1, 9)

                            st.rerun()


    # ========================================================
    # IMAGE RECOGNITION / IMAGE MEMORY GAME
    # ========================================================

    if active_game == "Image Recognition":

        st.subheader("🖼️ Image Recognition Game")

        image_game_config = IMAGE_GAME_DIFFICULTY[difficulty]
        image_target_count = image_game_config["target_count"]
        image_choice_count = image_game_config["choice_count"]

        st.write(
            f"Remember {image_target_count} images. "
            "They remain visible for exactly 10 seconds. "
            "The answer choices activate only after the timer reaches 0."
        )

        st.info(
            "🧠 How it works: memorize the image cards → watch the countdown "
            "10 → 9 → 8 → ... → 1 → 0 → images disappear → answer section activates."
        )

        # ----------------------------------------------------
        # START IMAGE GAME
        # ----------------------------------------------------
        if st.session_state.image_memory_round == 0:

            st.markdown(
                f"### 🎯 {total_rounds} rounds | "
                f"{image_target_count} images to remember | "
                f"{image_choice_count} answer choices"
            )

            st.markdown(
                "**Important:** Do not select anything during the 10-second "
                "viewing phase. Selection becomes available automatically at 0 seconds."
            )

            if st.button(
                "▶️ Start Image Recognition Game",
                type="primary",
                key="image_memory_start",
                use_container_width=True
            ):

                st.session_state.image_memory_total_score = 0.0

                prepare_image_memory_round(
                    difficulty,
                    1
                )

                queue_voice(
                    f"Image Recognition Game started. Round 1 of {total_rounds}. "
                    f"Remember {image_target_count} images for 10 seconds.",
                    language
                )

                st.rerun()

        # ----------------------------------------------------
        # ACTIVE IMAGE GAME
        # ----------------------------------------------------
        else:

            current_round = st.session_state.image_memory_round

            target_images = st.session_state.image_memory_sequence

            answer_choices = st.session_state.get(
                "image_memory_choices",
                []
            )

            st.progress(
                current_round / total_rounds,
                text=f"Round {current_round} of {total_rounds}"
            )

            # ------------------------------------------------
            # VIEWING PHASE
            # ------------------------------------------------
            remaining = image_remaining_seconds()

            if remaining > 0:

                st.session_state.image_memory_answer_phase = False

                st.markdown(
                    "### 👀 Memorize these images"
                )

                st.markdown(
                    render_image_cards(target_images),
                    unsafe_allow_html=True
                )

                st.markdown(
                    image_countdown_banner(remaining),
                    unsafe_allow_html=True
                )

                st.caption(
                    "🔒 Answer controls are locked. They will appear after the countdown reaches 0."
                )

                if st_autorefresh is not None:

                    st_autorefresh(
                        interval=1000,
                        limit=11,
                        key=f"image_memory_timer_{user_id}_{current_round}"
                    )

                else:

                    st.error(
                        "Countdown dependency is missing. "
                        "Install streamlit-autorefresh and restart the app."
                    )

            # ------------------------------------------------
            # ANSWER PHASE
            # ------------------------------------------------
            else:

                if not st.session_state.image_memory_answer_phase:

                    st.session_state.image_memory_answer_phase = True
                    st.session_state.image_memory_start_time = None
                    st.session_state.image_memory_selected = []

                    st.rerun()

                st.markdown(
                    image_countdown_banner(0),
                    unsafe_allow_html=True
                )

                st.success(
                    "✅ Time is up! The images have disappeared. "
                    "The answer choices are now active."
                )

                st.markdown(
                    f"### 🧠 Select exactly {image_target_count} images you remember"
                )

                selected_keys = []

                choice_columns = st.columns(4)

                for index, image_key in enumerate(answer_choices):

                    with choice_columns[index % 4]:

                        st.markdown(
                            render_image_cards(
                                [image_key],
                                compact=True
                            ),
                            unsafe_allow_html=True
                        )

                        checked = st.checkbox(
                            f"Select {IMAGE_GAME_ITEMS[image_key]['label']}",
                            key=(
                                f"image_choice_{user_id}_"
                                f"{current_round}_{image_key}"
                            )
                        )

                        if checked:
                            selected_keys.append(image_key)

                st.session_state.image_memory_selected = selected_keys

                st.markdown(
                    f"**Selected: {len(selected_keys)} / {image_target_count}**"
                )

                exit_col, submit_col = st.columns(2)

                with exit_col:

                    if st.button(
                        "🚪 Exit Image Game",
                        key=f"image_exit_{current_round}",
                        use_container_width=True
                    ):

                        exit_current_game(
                            "Image Recognition"
                        )

                with submit_col:

                    if st.button(
                        "✅ Submit Image Answer",
                        key=f"image_submit_{current_round}",
                        type="primary",
                        use_container_width=True
                    ):

                        if len(selected_keys) != image_target_count:

                            st.error(
                                f"Please select exactly {image_target_count} images before submitting."
                            )

                        else:

                            correct = sum(
                                image_key in target_images
                                for image_key in selected_keys
                            )

                            round_score = (
                                correct /
                                image_target_count
                            ) * 100

                            st.session_state.image_memory_total_score += round_score

                            st.success(
                                f"Round {current_round}: {correct} of "
                                f"{image_target_count} images correct "
                                f"({round_score:.0f}/100)."
                            )

                            if current_round >= total_rounds:

                                final_score = (
                                    st.session_state.image_memory_total_score /
                                    total_rounds
                                )

                                old_difficulty, new_difficulty, result = (
                                    update_adaptive_difficulty(
                                        user_id,
                                        final_score
                                    )
                                )

                                save_image_game_result(
                                    final_score,
                                    old_difficulty,
                                    new_difficulty
                                )

                                reset_image_memory_game()

                                queue_voice(
                                    game_result_voice(
                                        "Image Recognition Game",
                                        round(final_score, 1),
                                        old_difficulty,
                                        new_difficulty,
                                        language
                                    ),
                                    language
                                )

                                st.rerun()

                            else:

                                next_round = current_round + 1

                                prepare_image_memory_round(
                                    difficulty,
                                    next_round
                                )

                                queue_voice(
                                    f"Round {current_round} completed. "
                                    f"Starting image round {next_round} of {total_rounds}. "
                                    f"You have 10 seconds to remember the images.",
                                    language
                                )

                                st.rerun()


# ============================================================
# REMINDERS
# ============================================================

elif selected_page == "reminders":

    st.title(
        "⏰ " +
        text(
            "reminders",
            language
        )
    )

    st.subheader(
        "➕ Add New Reminder"
    )

    reminder_title = st.text_input(
        "Reminder Title",
        placeholder="Example: Drink water",
        key="reminder_title"
    )

    reminder_time = st.time_input(
        "Reminder Time",
        value=time(9, 0),
        key="reminder_time"
    )

    if st.button(
        "➕ Add Reminder",
        type="primary"
    ):

        if not reminder_title.strip():

            queue_voice(
                "Please enter a reminder.",
                language
            )

            st.error(
                "Please enter a reminder."
            )

        else:

            formatted_time = (
                reminder_time.strftime(
                    "%H:%M"
                )
            )

            conn.execute(
                """
                INSERT INTO reminders(
                    user_id,
                    title,
                    due_time,
                    status
                )
                VALUES(
                    ?,
                    ?,
                    ?,
                    'Pending'
                )
                """,
                (
                    user_id,
                    reminder_title.strip(),
                    (
                        f"{date.today()} "
                        f"{formatted_time}"
                    )
                )
            )

            conn.commit()

            queue_voice(
                (
                    f"{reminder_title.strip()} "
                    f"reminder has been added "
                    f"for {formatted_time}."
                ),
                language
            )

            st.rerun()

    st.divider()

    reminders = conn.execute(
        """
        SELECT
            id,
            title,
            due_time,
            status
        FROM reminders
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (
            user_id,
        )
    ).fetchall()

    if not reminders:

        st.info(
            "No reminders added yet."
        )

    else:

        for reminder in reminders:

            col1, col2, col3, col4 = st.columns(
                [4, 2, 1, 1]
            )

            col1.write(
                f"**{reminder[1]}**"
            )

            col2.write(
                reminder[2]
            )

            if reminder[3] == "Done":

                col3.success(
                    "Done"
                )

            else:

                if col3.button(
                    "Done",
                    key=f"reminder_done_{reminder[0]}"
                ):

                    conn.execute(
                        """
                        UPDATE reminders
                        SET status='Done'
                        WHERE id=?
                        AND user_id=?
                        """,
                        (
                            reminder[0],
                            user_id
                        )
                    )

                    conn.commit()

                    queue_voice(
                        (
                            f"Congratulations! "
                            f"You completed your reminder: "
                            f"{reminder[1]}."
                        ),
                        language
                    )

                    st.rerun()

            if col4.button(
                "Delete",
                key=f"reminder_delete_{reminder[0]}"
            ):

                conn.execute(
                    """
                    DELETE FROM reminders
                    WHERE id=?
                    AND user_id=?
                    """,
                    (
                        reminder[0],
                        user_id
                    )
                )

                conn.commit()

                queue_voice(
                    "Reminder deleted successfully.",
                    language
                )

                st.rerun()


# ============================================================
# HISTORY
# ============================================================

elif selected_page == "history":

    st.title(
        "📜 " +
        text(
            "history",
            language
        )
    )

    sessions = conn.execute(
        """
        SELECT
            game,
            score,
            difficulty,
            created_at
        FROM sessions
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    if not sessions:

        st.info(
            text(
                "no_history",
                language
            )
        )

    else:

        c1, c2, c3 = st.columns(3)

        scores = [
            float(row[1])
            for row in sessions
        ]

        c1.metric(
            "Personal Baseline",
            f"{baseline:.1f}"
        )

        c2.metric(
            "Average",
            f"{sum(scores) / len(scores):.1f}"
        )

        c3.metric(
            "Current Difficulty",
            difficulty
        )

        st.subheader(
            "📈 Last 5 Games Progress"
        )

        last_five = sessions[:5][::-1]

        graph_df = pd.DataFrame(
            [
                {
                    "Game": f"{index}. {row[0]}",
                    "Score": float(row[1])
                }
                for index, row in enumerate(last_five, start=1)
            ]
        )

        if not graph_df.empty:

            st.line_chart(
                graph_df.set_index("Game"),
                y="Score",
                use_container_width=True
            )

            st.caption(
                "The graph shows the five most recently completed games, "
                "with the oldest of those five first. Scores are final "
                "scores saved for each completed multi-round game."
            )

        st.dataframe(
            [
                {
                    "Game": row[0],
                    "Score": row[1],
                    "Difficulty": row[2],
                    "Date": row[3]
                }
                for row in sessions
            ],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# DETAILS
# ============================================================

elif selected_page == "details":

    st.title(
        "👤 " +
        text(
            "details",
            language
        )
    )

    st.write(
        f"**Name:** {name}"
    )

    st.write(
        f"**Username:** {username}"
    )

    st.write(
        "**Role:** Patient"
    )

    st.write(
        f"**Language:** {language}"
    )

    st.write(
        f"**Personal Baseline:** {baseline:.1f}"
    )

    st.write(
        f"**Adaptive Difficulty:** "
        f"{difficulty}/3"
    )

    st.write(f"**Phone:** {phone}")
    st.write(f"**Email:** {email}")
    st.write(f"**Location:** {location}")

    if doctor_id:

        doctor = conn.execute(
            """
            SELECT name, username, phone, email, location
            FROM users
            WHERE id=?
            AND role='doctor'
            """,
            (doctor_id,)
        ).fetchone()

        if doctor:
            st.success(
                f"🩺 Assigned Doctor: Dr. {doctor[0]}"
            )
            st.write(f"Doctor Username: {doctor[1]}")
            st.write(f"Doctor Phone: {doctor[2]}")
            st.write(f"Doctor Email: {doctor[3]}")
            st.write(f"Doctor Location: {doctor[4]}")

    elif caretaker_id:

        caretaker = conn.execute(
            """
            SELECT name, username, phone, email, location
            FROM users
            WHERE id=?
            AND role='caretaker'
            """,
            (caretaker_id,)
        ).fetchone()

        if caretaker:
            st.success(
                f"🤝 Assigned Caretaker: {caretaker[0]}"
            )
            st.write(f"Caretaker Username: {caretaker[1]}")
            st.write(f"Caretaker Phone: {caretaker[2]}")
            st.write(f"Caretaker Email: {caretaker[3]}")
            st.write(f"Caretaker Location: {caretaker[4]}")

    else:

        st.info(
            "No doctor or caretaker linked yet. A provider can add the patient directly."
        )


# ============================================================
# REPORTS
# ============================================================

elif selected_page == "reports":

    st.title(
        "📄 " +
        text(
            "reports",
            language
        )
    )

    # ------------------------------------------------------------
    # CLINICAL-STYLE APPLICATION REPORT
    # ------------------------------------------------------------

    st.subheader("🧾 Cognitive Progress Report")
    st.caption(
        "This report uses the same sectioned, professional visual style as the "
        "reference document, but only includes data available in MINDSETU NER."
    )

    if REPORTLAB_AVAILABLE:

        clinical_pdf = build_patient_progress_pdf(
            user_id
        )

        if clinical_pdf:
            st.download_button(
                "⬇️ Download Cognitive Progress Report PDF",
                data=clinical_pdf,
                file_name=(
                    f"MINDSETU_NER_Cognitive_Report_"
                    f"{username}.pdf"
                ),
                mime="application/pdf",
                use_container_width=True
            )

            st.success(
                "Report generated successfully. "
                "The PDF contains your profile, longitudinal metrics, "
                "game performance, reminders, and session audit log."
            )

    else:
        st.warning(
            "PDF generation requires ReportLab. "
            "Install it with: pip install reportlab"
        )

    st.divider()

    # ------------------------------------------------------------
    # DOCTOR REPORTS ALREADY SENT TO THE PATIENT
    # ------------------------------------------------------------

    reports = conn.execute(
        """
        SELECT
            r.id,
            r.title,
            r.report_text,
            r.created_at,
            d.name
        FROM reports r
        INNER JOIN users d
        ON r.doctor_id=d.id
        WHERE r.patient_id=?
        ORDER BY r.id DESC
        """,
        (
            user_id,
        )
    ).fetchall()

    if not reports:

        st.info(
            text(
                "no_reports",
                language
            )
        )

    else:

        st.subheader("📨 Reports Sent by Doctor")

        for report in reports:

            with st.expander(
                f"📄 {report[1]} — {report[3]}"
            ):

                st.write(
                    f"🩺 Doctor: Dr. {report[4]}"
                )

                st.divider()

                st.write(
                    report[2]
                )

                if st.button(
                    "🔊 Listen to Report",
                    key=f"listen_report_{report[0]}"
                ):

                    queue_voice(
                        report[2],
                        language
                    )

                    st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🧠 MINDSETU NER | Cognitive Wellness Prototype"
)

st.caption(
    "For demonstration and educational purposes only. "
    "This prototype does not provide medical diagnosis."
)
