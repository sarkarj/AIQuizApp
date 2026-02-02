"""
AI Quiz Platform - Analytics View Component
Version: 1.1.0
Changelog: Removed "Refresh Stats" and "Take Another Quiz" buttons (Issue 2)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from services.user_service import user_service
from utils.helpers import get_performance_emoji

def render_analytics_view():
    """Render user performance analytics"""
    
    st.title("📊 My Performance")
    st.markdown(f"Welcome back, **{st.session_state.username}**!")
    st.markdown("---")
    
    # Get user stats
    stats = user_service.get_user_stats(st.session_state.user_id)
    
    if stats['total_attempts'] == 0:
        st.info("📚 You haven't taken any quizzes yet. Start your learning journey now!")
        st.markdown("### 🎯 How to Get Started")
        st.markdown("""
        1. Click on **'🎯 Take Quiz'** in the sidebar
        2. Select a quiz that interests you
        3. Choose the number of questions and difficulty level
        4. Start answering and get instant AI-powered feedback!
        5. Come back here to track your progress over time
        """)
        st.markdown("---")
        st.success("💡 **Tip:** The more quizzes you take, the more insights you'll see here about your learning progress!")
        return
    
    # Overview metrics
    st.subheader("📈 Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Attempts", stats['total_attempts'])
    
    with col2:
        emoji = get_performance_emoji(stats['average_score'])
        st.metric("Average Score", f"{stats['average_score']}% {emoji}")
    
    with col3:
        st.metric("Best Score", f"{stats['best_score']}%", delta=None)
    
    with col4:
        trend_color = "normal"
        if "Improving" in stats['recent_trend']:
            trend_color = "normal"
        elif "Declining" in stats['recent_trend']:
            trend_color = "inverse"
        
        st.metric("Recent Trend", stats['recent_trend'], delta_color=trend_color)
    
    st.info("💡 Keep going! Every attempt makes you stronger! 💪")
    st.markdown("---")
    
    left_col, right_col = st.columns([2, 3])

    with left_col:
        # Performance trend chart
        st.subheader("📉 Performance Trend")
        
        trend_data = user_service.get_performance_trend(st.session_state.user_id, limit=20)
        
        if trend_data:
            df = pd.DataFrame(trend_data)
            df['completed_at'] = pd.to_datetime(df['completed_at'])
            
            # Create line chart
            fig = px.line(
                df,
                x='attempt_number',
                y='score',
                title='Score Progress Over Time',
                labels={'attempt_number': 'Attempt Number', 'score': 'Score (%)'},
                markers=True
            )
            
            # Add average line
            fig.add_hline(
                y=stats['average_score'],
                line_dash="dash",
                line_color="green",
                annotation_text=f"Average: {stats['average_score']}%"
            )
            
            # Customize layout
            fig.update_layout(
                yaxis_range=[0, 100],
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Calculate improvement
            if len(df) >= 2:
                first_score = df.iloc[0]['score']
                last_score = df.iloc[-1]['score']
                improvement = last_score - first_score
                
                if improvement > 0:
                    st.success(f"🚀 You've improved by {improvement:.1f}% since your first attempt! Keep it up!")
                elif improvement < 0:
                    st.info(f"💪 Don't worry about the {abs(improvement):.1f}% dip. Keep practicing!")
                else:
                    st.info("📊 Your performance is consistent. Try challenging yourself with harder questions!")

    with right_col:
        # Attempt history
        st.subheader("📜 Attempt History")
        
        history = user_service.get_attempt_history(st.session_state.user_id, limit=10)
        
        if history:
            # Create dataframe for display
            history_df = pd.DataFrame(history)
            history_df['Date'] = pd.to_datetime(history_df['started_at']).dt.strftime('%Y-%m-%d %H:%M')
            history_df['Score'] = history_df['score_percentage'].round(1).astype(str) + '%'
            history_df['Questions'] = history_df['correct_count'].astype(str) + '/' + history_df['total_questions'].astype(str)
            
            # Display table (4 columns only)
            display_df = history_df[['Date', 'quiz_name', 'Questions', 'Score']]
            display_df.columns = ['Date', 'Quiz Name', 'Questions', 'Score']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Detailed view option
            with st.expander("🔍 View Detailed Results"):
                selected_attempt_index = st.selectbox(
                    "Select an attempt to view details",
                    range(len(history)),
                    format_func=lambda i: f"{history_df.iloc[i]['Date']} - {history_df.iloc[i]['quiz_name']} ({history_df.iloc[i]['Score']})"
                )
                
                if selected_attempt_index is not None:
                    attempt_id = history[selected_attempt_index]['quiz_attempt_id']
                    render_attempt_details(attempt_id)
    
    st.markdown("---")

def render_attempt_details(quiz_attempt_id):
    """Render detailed results for a specific attempt"""
    
    from services.quiz_service import quiz_service
    
    question_attempts = quiz_service.get_attempt_question_details(quiz_attempt_id)
    
    if not question_attempts:
        st.warning("No details available for this attempt")
        return
    
    st.markdown("#### Question-by-Question Breakdown")
    
    for idx, qa in enumerate(question_attempts, 1):
        status_icon = "✅" if qa['is_correct'] else ("⭐" if qa['skipped'] else "❌")
        
        with st.expander(f"{status_icon} Question {idx}: {qa['question_text'][:80]}..."):
            st.markdown(f"**Question:** {qa['question_text']}")

            st.markdown("**Options:**")
            options = qa.get('options_text', '')
            correct = set((qa.get('correct_answer') or '').replace(' ', '').split(','))
            user_answer = set((qa.get('user_answer') or '').replace(' ', '').split(','))
            for line in options.split('\n'):
                line = line.strip()
                if not line:
                    continue
                letter = line[0].upper()
                if letter in correct:
                    st.success(f"✅ {line}")
                elif letter in user_answer and not qa['skipped']:
                    st.error(f"❌ {line}")
                else:
                    st.markdown(line)
            
            if qa['llm_explanation']:
                st.markdown("**Explanation:**")
                st.info(qa['llm_explanation'])
