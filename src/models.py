"""
Data Contracts for Autonomous AI Researcher

Defines Pydantic models for:
- ResearchIdea: Research ideas with hypothesis and methodology
- ExperimentResult: Results from executed experiments
- PaperDraft: Structured paper drafts
- ResearchGap: Identified gaps in literature
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
from datetime import datetime
import uuid
import json


class ResearchGap(BaseModel):
    """Identified gap in research literature"""
    topic: str
    description: str
    keywords: List[str] = Field(default_factory=list)
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    model_config = {"arbitrary_types_allowed": True}
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return self.model_dump_json(indent=2)


class ResearchIdea(BaseModel):
    """A research idea with hypothesis and methodology"""
    title: str
    hypothesis: str
    methodology: str
    research_domain: str = "AI/ML"
    keywords: List[str] = Field(default_factory=list)
    status: str = "proposed"
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = {"arbitrary_types_allowed": True}
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = ['proposed', 'in_progress', 'completed', 'rejected']
        if v not in allowed:
            raise ValueError(f'status must be one of {allowed}')
        return v
    
    def validate(self) -> bool:
        """Validate the research idea has all required fields"""
        return bool(self.title and self.hypothesis and self.methodology)
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return self.model_dump_json(indent=2)


class ExperimentResult(BaseModel):
    """Results from an executed experiment"""
    experiment_id: str
    idea_id: str
    status: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = {"arbitrary_types_allowed": True}
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = ['running', 'completed', 'failed', 'cancelled']
        if v not in allowed:
            raise ValueError(f'status must be one of {allowed}')
        return v
    
    def validate(self) -> bool:
        """Validate the experiment result"""
        return bool(self.experiment_id and self.idea_id)
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return self.model_dump_json(indent=2)


class PaperSection(BaseModel):
    """A section of a paper"""
    name: str
    content: str
    order: int = 0


class PaperDraft(BaseModel):
    """A structured paper draft"""
    title: str
    abstract: str
    research_idea: ResearchIdea
    experiment_results: List[ExperimentResult] = Field(default_factory=list)
    sections: Dict[str, str] = Field(default_factory=dict)
    references: List[Dict[str, str]] = Field(default_factory=list)
    status: str = "draft"
    output_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = {"arbitrary_types_allowed": True}
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = ['draft', 'review', 'final']
        if v not in allowed:
            raise ValueError(f'status must be one of {allowed}')
        return v
    
    def validate(self) -> bool:
        """Validate the paper draft has required components"""
        return bool(
            self.title and 
            self.abstract and 
            self.research_idea and
            len(self.sections) > 0
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return self.model_dump_json(indent=2)
    
    def to_latex(self) -> str:
        """Generate LaTeX representation (basic implementation)"""
        latex = f"""\\documentclass{{article}}
\\title{{{self.title}}}
\\begin{{document}}
\\maketitle

\\begin{{abstract}}
{self.abstract}
\\end{{abstract}}

"""
        for section_name, content in self.sections.items():
            latex += f"\\section{{{section_name.capitalize()}}}\n"
            latex += f"{content}\n\n"
        
        latex += "\\end{document}"
        return latex
