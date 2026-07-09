"""EMBEDHUNT AI — AI Agent layer.

Each agent follows the same pipeline:
    Input -> ContextBuilder -> PromptTemplate -> AIRouter -> ResponseParser
          -> MemoryStore -> Output
"""
from app.agents.base_agent import BaseAgent
from app.agents.coding_agent import CodingAgent
from app.agents.interview_agent import InterviewAgent
from app.agents.learning_agent import LearningAgent
from app.agents.matching_agent import MatchingAgent
from app.agents.mentor_agent import MentorAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.roadmap_agent import RoadmapAgent
from app.agents.salary_agent import SalaryAgent

__all__ = [
    "BaseAgent",
    "ResumeAgent",
    "MatchingAgent",
    "MentorAgent",
    "InterviewAgent",
    "RoadmapAgent",
    "SalaryAgent",
    "LearningAgent",
    "CodingAgent",
]
