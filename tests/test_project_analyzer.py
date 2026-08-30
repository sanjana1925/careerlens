from app.services import project_analyzer


def test_categorize_matches_known_keywords():
    assert project_analyzer.categorize("A house price prediction regression model") == "supervised-ml-prediction"
    assert project_analyzer.categorize("A RAG pipeline over internal docs") == "rag"
    assert project_analyzer.categorize("Just a plain description with nothing special") is None


def test_analyze_projects_flags_repeated_categories():
    projects = [
        {"title": "House Prices", "description": "A regression model predicting house prices."},
        {"title": "Student Grades", "description": "A classifier predicting student grades."},
        {"title": "RAG Chatbot", "description": "A retrieval augmented generation chatbot."},
    ]

    findings, suggestions = project_analyzer.analyze_projects(projects)

    by_title = {f.title: f for f in findings}
    assert by_title["House Prices"].category == "supervised-ml-prediction"
    assert by_title["House Prices"].is_repetitive is True
    assert by_title["Student Grades"].is_repetitive is True
    assert by_title["RAG Chatbot"].is_repetitive is False
    assert len(suggestions) == 1


def test_analyze_projects_no_repetition_yields_no_suggestions():
    projects = [
        {"title": "RAG Chatbot", "description": "A retrieval augmented generation chatbot."},
        {"title": "CV Detector", "description": "An object detection model using opencv."},
    ]

    findings, suggestions = project_analyzer.analyze_projects(projects)

    assert all(not f.is_repetitive for f in findings)
    assert suggestions == []


def test_heuristic_segment_extracts_projects_section():
    resume_text = """
John Doe

EXPERIENCE
Software Engineer at Acme

PROJECTS
Resume Analyzer
- Built a Python tool that scores resumes.
- Deployed with Docker.

Job Board Scraper
- Scraped job postings from multiple sources.

EDUCATION
BS Computer Science
""".strip()

    projects = project_analyzer._heuristic_segment(resume_text)

    titles = [p["title"] for p in projects]
    assert titles == ["Resume Analyzer", "Job Board Scraper"]
    assert "Python tool" in projects[0]["description"]


def test_heuristic_segment_no_projects_section_returns_empty():
    resume_text = "EXPERIENCE\nSoftware Engineer at Acme\n\nEDUCATION\nBS Computer Science"
    assert project_analyzer._heuristic_segment(resume_text) == []
