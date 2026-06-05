"""
论文写作Agent

负责论文写作、润色、格式化和引用管理。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from loguru import logger

from ..core.agent_base import AgentBase, AgentResult
from ..services.llm_service import LLMService


class DocumentSection(BaseModel):
    """文档章节"""
    id: str = Field(..., description="章节ID")
    title: str = Field(..., description="章节标题")
    content: str = Field("", description="章节内容")
    level: int = Field(1, description="章节级别")
    order: int = Field(0, description="章节顺序")
    word_count: int = Field(0, description="字数")
    status: str = Field("draft", description="状态 (draft, review, final)")
    notes: List[str] = Field(default_factory=list, description="备注")


class Document(BaseModel):
    """文档模型"""
    id: str = Field(..., description="文档ID")
    title: str = Field(..., description="文档标题")
    authors: List[str] = Field(default_factory=list, description="作者列表")
    abstract: str = Field("", description="摘要")
    keywords: List[str] = Field(default_factory=list, description="关键词")
    sections: List[DocumentSection] = Field(default_factory=list, description="章节列表")
    references: List[Dict[str, Any]] = Field(default_factory=list, description="参考文献")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    word_count: int = Field(0, description="总字数")
    status: str = Field("draft", description="文档状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class WritingFeedback(BaseModel):
    """写作反馈"""
    section_id: str = Field(..., description="章节ID")
    feedback_type: str = Field(..., description="反馈类型")
    severity: str = Field("info", description="严重程度")
    message: str = Field(..., description="反馈信息")
    suggestion: str = Field("", description="建议")
    location: str = Field("", description="位置")
    auto_fixable: bool = Field(False, description="是否可自动修复")


class WritingAgent(AgentBase):
    """
    论文写作Agent
    
    负责论文写作、润色、格式化和引用管理。
    
    Features:
        - 论文结构生成
        - 内容撰写
        - 语言润色
        - 格式检查
        - 引用管理
        - 写作反馈
        - 多语言支持
    """
    
    def __init__(self, llm_service: LLMService, name: str = "WritingAgent"):
        """
        初始化论文写作Agent
        
        Args:
            llm_service: LLM服务
            name: Agent名称
        """
        super().__init__(name=name)
        self.llm_service = llm_service
        self._logger = logger.bind(module="WritingAgent")
        
        # 文档存储
        self._documents: Dict[str, Document] = {}
        
        # 写作模板
        self._templates: Dict[str, Dict[str, Any]] = {
            "research_paper": {
                "title": "Research Paper",
                "sections": [
                    {"title": "Abstract", "level": 1, "order": 1},
                    {"title": "Introduction", "level": 1, "order": 2},
                    {"title": "Literature Review", "level": 1, "order": 3},
                    {"title": "Methodology", "level": 1, "order": 4},
                    {"title": "Results", "level": 1, "order": 5},
                    {"title": "Discussion", "level": 1, "order": 6},
                    {"title": "Conclusion", "level": 1, "order": 7},
                    {"title": "References", "level": 1, "order": 8},
                ],
            },
            "review_paper": {
                "title": "Review Paper",
                "sections": [
                    {"title": "Abstract", "level": 1, "order": 1},
                    {"title": "Introduction", "level": 1, "order": 2},
                    {"title": "Background", "level": 1, "order": 3},
                    {"title": "Literature Review", "level": 1, "order": 4},
                    {"title": "Analysis", "level": 1, "order": 5},
                    {"title": "Discussion", "level": 1, "order": 6},
                    {"title": "Conclusion", "level": 1, "order": 7},
                    {"title": "References", "level": 1, "order": 8},
                ],
            },
            "thesis": {
                "title": "Thesis",
                "sections": [
                    {"title": "Abstract", "level": 1, "order": 1},
                    {"title": "Acknowledgements", "level": 1, "order": 2},
                    {"title": "Table of Contents", "level": 1, "order": 3},
                    {"title": "List of Figures", "level": 1, "order": 4},
                    {"title": "List of Tables", "level": 1, "order": 5},
                    {"title": "Chapter 1: Introduction", "level": 1, "order": 6},
                    {"title": "Chapter 2: Literature Review", "level": 1, "order": 7},
                    {"title": "Chapter 3: Methodology", "level": 1, "order": 8},
                    {"title": "Chapter 4: Results", "level": 1, "order": 9},
                    {"title": "Chapter 5: Discussion", "level": 1, "order": 10},
                    {"title": "Chapter 6: Conclusion", "level": 1, "order": 11},
                    {"title": "References", "level": 1, "order": 12},
                    {"title": "Appendices", "level": 1, "order": 13},
                ],
            },
        }
        
        # 写作风格指南
        self._style_guides: Dict[str, Dict[str, Any]] = {
            "academic": {
                "tone": "formal",
                "perspective": "third_person",
                "tense": "past",
                "voice": "passive",
                "contractions": False,
                "personal_pronouns": False,
                "citation_style": "APA",
            },
            "conversational": {
                "tone": "informal",
                "perspective": "first_person",
                "tense": "present",
                "voice": "active",
                "contractions": True,
                "personal_pronouns": True,
                "citation_style": "APA",
            },
        }
    
    async def execute(self, **kwargs) -> AgentResult:
        """
        执行论文写作任务
        
        Args:
            **kwargs: 任务参数
                - action: 操作类型 (create, write, edit, polish, format, feedback, export)
                - document_id: 文档ID
                - section_id: 章节ID
                - content: 内容
                - template: 模板
                - style: 风格
                
        Returns:
            AgentResult: 执行结果
        """
        action = kwargs.get("action", "create")
        
        try:
            if action == "create":
                result = await self.create_document(
                    title=kwargs["title"],
                    authors=kwargs.get("authors", []),
                    template=kwargs.get("template", "research_paper"),
                )
            elif action == "write":
                result = await self.write_section(
                    document_id=kwargs["document_id"],
                    section_id=kwargs.get("section_id"),
                    content=kwargs.get("content", ""),
                    topic=kwargs.get("topic", ""),
                )
            elif action == "edit":
                result = await self.edit_section(
                    document_id=kwargs["document_id"],
                    section_id=kwargs["section_id"],
                    content=kwargs.get("content", ""),
                    operation=kwargs.get("operation", "replace"),
                )
            elif action == "polish":
                result = await self.polish_text(
                    text=kwargs["text"],
                    style=kwargs.get("style", "academic"),
                    focus=kwargs.get("focus", "all"),
                )
            elif action == "format":
                result = await self.format_document(
                    document_id=kwargs["document_id"],
                    format_style=kwargs.get("format_style", "APA"),
                )
            elif action == "feedback":
                result = await self.provide_feedback(
                    document_id=kwargs["document_id"],
                    section_id=kwargs.get("section_id"),
                )
            elif action == "export":
                result = await self.export_document(
                    document_id=kwargs["document_id"],
                    format=kwargs.get("format", "markdown"),
                )
            elif action == "generate":
                result = await self.generate_content(
                    topic=kwargs["topic"],
                    content_type=kwargs.get("content_type", "paragraph"),
                    style=kwargs.get("style", "academic"),
                    length=kwargs.get("length", "medium"),
                )
            elif action == "summarize":
                result = await self.summarize_text(
                    text=kwargs["text"],
                    max_length=kwargs.get("max_length", 200),
                )
            elif action == "translate":
                result = await self.translate_text(
                    text=kwargs["text"],
                    target_language=kwargs.get("target_language", "en"),
                    source_language=kwargs.get("source_language", "auto"),
                )
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    agent_name=self.name,
                )
            
            return AgentResult(
                success=True,
                data=result,
                agent_name=self.name,
            )
            
        except Exception as e:
            self._logger.exception(f"Error in WritingAgent: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                agent_name=self.name,
            )
    
    async def create_document(
        self,
        title: str,
        authors: List[str] = None,
        template: str = "research_paper",
    ) -> Document:
        """
        创建文档
        
        Args:
            title: 文档标题
            authors: 作者列表
            template: 模板名称
            
        Returns:
            Document: 文档对象
        """
        self._logger.info(f"Creating document: {title}")
        
        # 生成文档ID
        doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 获取模板
        template_data = self._templates.get(template, self._templates["research_paper"])
        
        # 创建章节
        sections = []
        for section_data in template_data["sections"]:
            section = DocumentSection(
                id=f"{doc_id}_section_{section_data['order']}",
                title=section_data["title"],
                level=section_data["level"],
                order=section_data["order"],
            )
            sections.append(section)
        
        # 创建文档
        document = Document(
            id=doc_id,
            title=title,
            authors=authors or [],
            sections=sections,
            metadata={"template": template},
        )
        
        # 存储文档
        self._documents[doc_id] = document
        
        self._logger.info(f"Document created: {doc_id}")
        
        return document
    
    async def write_section(
        self,
        document_id: str,
        section_id: Optional[str] = None,
        content: str = "",
        topic: str = "",
    ) -> Dict[str, Any]:
        """
        撰写章节
        
        Args:
            document_id: 文档ID
            section_id: 章节ID
            content: 内容
            topic: 主题
            
        Returns:
            Dict[str, Any]: 撰写结果
        """
        self._logger.info(f"Writing section for document: {document_id}")
        
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self._documents[document_id]
        
        # 找到章节
        section = None
        if section_id:
            for s in document.sections:
                if s.id == section_id:
                    section = s
                    break
        else:
            # 如果没有指定章节，使用第一个空章节
            for s in document.sections:
                if not s.content:
                    section = s
                    break
        
        if not section:
            raise ValueError(f"Section not found or no empty sections available")
        
        # 如果提供了主题，使用LLM生成内容
        if topic and not content:
            content = await self._generate_section_content(
                section_title=section.title,
                topic=topic,
                document_title=document.title,
            )
        
        # 更新章节内容
        section.content = content
        section.word_count = len(content.split())
        section.status = "draft"
        
        # 更新文档
        document.updated_at = datetime.now()
        document.word_count = sum(s.word_count for s in document.sections)
        
        return {
            "document_id": document_id,
            "section_id": section.id,
            "section_title": section.title,
            "word_count": section.word_count,
            "status": section.status,
            "message": f"章节 '{section.title}' 已更新",
        }
    
    async def _generate_section_content(
        self,
        section_title: str,
        topic: str,
        document_title: str,
    ) -> str:
        """
        生成章节内容
        
        Args:
            section_title: 章节标题
            topic: 主题
            document_title: 文档标题
            
        Returns:
            str: 生成的内容
        """
        prompt = f"""
        请为学术论文的以下章节撰写内容：
        
        论文标题：{document_title}
        章节标题：{section_title}
        主题：{topic}
        
        请按照学术写作规范撰写，内容应该：
        1. 逻辑清晰，结构完整
        2. 使用学术语言
        3. 包含适当的论据和支持
        4. 符合{section_title}章节的写作要求
        
        请直接输出内容，不要添加额外的说明。
        """
        
        content = await self.llm_service.generate(prompt)
        return content
    
    async def edit_section(
        self,
        document_id: str,
        section_id: str,
        content: str,
        operation: str = "replace",
    ) -> Dict[str, Any]:
        """
        编辑章节
        
        Args:
            document_id: 文档ID
            section_id: 章节ID
            content: 内容
            operation: 操作类型 (replace, append, prepend, insert)
            
        Returns:
            Dict[str, Any]: 编辑结果
        """
        self._logger.info(f"Editing section {section_id} in document {document_id}")
        
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self._documents[document_id]
        
        # 找到章节
        section = None
        for s in document.sections:
            if s.id == section_id:
                section = s
                break
        
        if not section:
            raise ValueError(f"Section {section_id} not found")
        
        # 执行操作
        if operation == "replace":
            section.content = content
        elif operation == "append":
            section.content += "\n\n" + content
        elif operation == "prepend":
            section.content = content + "\n\n" + section.content
        elif operation == "insert":
            # 在现有内容中间插入
            mid_point = len(section.content) // 2
            section.content = section.content[:mid_point] + "\n\n" + content + "\n\n" + section.content[mid_point:]
        
        # 更新统计
        section.word_count = len(section.content.split())
        section.status = "draft"
        
        # 更新文档
        document.updated_at = datetime.now()
        document.word_count = sum(s.word_count for s in document.sections)
        
        return {
            "document_id": document_id,
            "section_id": section_id,
            "operation": operation,
            "new_word_count": section.word_count,
            "message": f"章节已编辑",
        }
    
    async def polish_text(
        self,
        text: str,
        style: str = "academic",
        focus: str = "all",
    ) -> Dict[str, Any]:
        """
        润色文本
        
        Args:
            text: 文本内容
            style: 写作风格
            focus: 润色重点 (grammar, clarity, style, all)
            
        Returns:
            Dict[str, Any]: 润色结果
        """
        self._logger.info(f"Polishing text with style: {style}, focus: {focus}")
        
        # 获取风格指南
        style_guide = self._style_guides.get(style, self._style_guides["academic"])
        
        # 构建润色提示
        focus_instructions = {
            "grammar": "请重点检查和修正语法错误、拼写错误和标点符号错误。",
            "clarity": "请重点提高文本的清晰度和可读性，简化复杂句子，消除歧义。",
            "style": "请重点调整写作风格，使其符合学术写作规范。",
            "all": "请全面润色文本，包括语法、清晰度、风格和格式。",
        }
        
        prompt = f"""
        请润色以下学术文本：
        
        原文：
        {text}
        
        润色要求：
        - 风格：{style_guide['tone']}，{style_guide['perspective']}视角
        - 重点：{focus_instructions.get(focus, focus_instructions['all'])}
        
        请提供：
        1. 润色后的文本
        2. 主要修改说明
        3. 修改理由
        
        请以JSON格式输出：
        {{
            "polished_text": "润色后的文本",
            "changes": ["修改1", "修改2", ...],
            "reasons": ["理由1", "理由2", ...]
        }}
        """
        
        response = await self.llm_service.generate(prompt)
        
        try:
            import json
            result = json.loads(response)
        except:
            result = {
                "polished_text": response,
                "changes": ["文本已润色"],
                "reasons": ["提高学术写作质量"],
            }
        
        return result
    
    async def format_document(
        self,
        document_id: str,
        format_style: str = "APA",
    ) -> Dict[str, Any]:
        """
        格式化文档
        
        Args:
            document_id: 文档ID
            format_style: 格式风格
            
        Returns:
            Dict[str, Any]: 格式化结果
        """
        self._logger.info(f"Formatting document {document_id} with style: {format_style}")
        
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self._documents[document_id]
        
        # 格式化检查
        issues = []
        
        # 检查标题格式
        if not document.title[0].isupper():
            issues.append("标题首字母应大写")
        
        # 检查摘要长度
        abstract_section = None
        for section in document.sections:
            if section.title.lower() == "abstract":
                abstract_section = section
                break
        
        if abstract_section:
            word_count = len(abstract_section.content.split())
            if word_count > 300:
                issues.append(f"摘要过长（{word_count}词），建议控制在250词以内")
            elif word_count < 100:
                issues.append(f"摘要过短（{word_count}词），建议至少150词")
        
        # 检查章节完整性
        empty_sections = [s.title for s in document.sections if not s.content]
        if empty_sections:
            issues.append(f"以下章节为空：{', '.join(empty_sections)}")
        
        # 检查引用格式
        if format_style == "APA":
            # APA格式检查
            for section in document.sections:
                if "(" in section.content and ")" in section.content:
                    # 简单的APA引用格式检查
                    pass
        
        return {
            "document_id": document_id,
            "format_style": format_style,
            "issues": issues,
            "issue_count": len(issues),
            "message": f"文档格式检查完成，发现{len(issues)}个问题",
        }
    
    async def provide_feedback(
        self,
        document_id: str,
        section_id: Optional[str] = None,
    ) -> List[WritingFeedback]:
        """
        提供写作反馈
        
        Args:
            document_id: 文档ID
            section_id: 章节ID
            
        Returns:
            List[WritingFeedback]: 反馈列表
        """
        self._logger.info(f"Providing feedback for document: {document_id}")
        
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self._documents[document_id]
        
        feedback_list = []
        
        # 获取要反馈的章节
        sections_to_review = []
        if section_id:
            for section in document.sections:
                if section.id == section_id:
                    sections_to_review.append(section)
                    break
        else:
            sections_to_review = [s for s in document.sections if s.content]
        
        for section in sections_to_review:
            # 使用LLM分析章节
            prompt = f"""
            请分析以下学术论文章节，提供详细的写作反馈：
            
            章节标题：{section.title}
            内容：
            {section.content}
            
            请从以下方面提供反馈：
            1. 内容完整性和深度
            2. 逻辑结构和连贯性
            3. 语言表达和学术规范
            4. 论证强度和证据支持
            5. 格式和引用
            
            请以JSON格式输出反馈列表：
            [
                {{
                    "feedback_type": "content|structure|language|argumentation|format",
                    "severity": "info|warning|error",
                    "message": "反馈信息",
                    "suggestion": "改进建议",
                    "location": "具体位置",
                    "auto_fixable": false
                }}
            ]
            """
            
            response = await self.llm_service.generate(prompt)
            
            try:
                import json
                feedback_data = json.loads(response)
                
                for item in feedback_data:
                    feedback = WritingFeedback(
                        section_id=section.id,
                        feedback_type=item.get("feedback_type", "general"),
                        severity=item.get("severity", "info"),
                        message=item.get("message", ""),
                        suggestion=item.get("suggestion", ""),
                        location=item.get("location", ""),
                        auto_fixable=item.get("auto_fixable", False),
                    )
                    feedback_list.append(feedback)
                    
            except:
                # 如果解析失败，创建通用反馈
                feedback = WritingFeedback(
                    section_id=section.id,
                    feedback_type="general",
                    severity="info",
                    message="章节内容已分析",
                    suggestion="请考虑进一步完善内容",
                )
                feedback_list.append(feedback)
        
        return feedback_list
    
    async def export_document(
        self,
        document_id: str,
        format: str = "markdown",
    ) -> Dict[str, Any]:
        """
        导出文档
        
        Args:
            document_id: 文档ID
            format: 导出格式
            
        Returns:
            Dict[str, Any]: 导出结果
        """
        self._logger.info(f"Exporting document {document_id} to {format}")
        
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self._documents[document_id]
        
        # 生成导出内容
        if format == "markdown":
            content = self._to_markdown(document)
        elif format == "latex":
            content = self._to_latex(document)
        elif format == "html":
            content = self._to_html(document)
        elif format == "plain":
            content = self._to_plain_text(document)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{document_id}_{timestamp}.{format}"
        
        return {
            "document_id": document_id,
            "format": format,
            "filename": filename,
            "content": content,
            "word_count": document.word_count,
            "section_count": len(document.sections),
            "message": f"文档已导出为{format}格式",
        }
    
    def _to_markdown(self, document: Document) -> str:
        """转换为Markdown格式"""
        lines = []
        
        # 标题
        lines.append(f"# {document.title}")
        lines.append("")
        
        # 作者
        if document.authors:
            lines.append(f"**Authors:** {', '.join(document.authors)}")
            lines.append("")
        
        # 章节
        for section in sorted(document.sections, key=lambda s: s.order):
            # 章节标题
            prefix = "#" * (section.level + 1)
            lines.append(f"{prefix} {section.title}")
            lines.append("")
            
            # 章节内容
            if section.content:
                lines.append(section.content)
                lines.append("")
        
        # 参考文献
        if document.references:
            lines.append("## References")
            lines.append("")
            for i, ref in enumerate(document.references, 1):
                lines.append(f"{i}. {ref.get('text', '')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _to_latex(self, document: Document) -> str:
        """转换为LaTeX格式"""
        lines = []
        
        # 文档类
        lines.append("\\documentclass[12pt]{article}")
        lines.append("\\usepackage[utf8]{inputenc}")
        lines.append("\\usepackage{amsmath}")
        lines.append("\\usepackage{graphicx}")
        lines.append("\\usepackage{hyperref}")
        lines.append("")
        
        # 标题
        lines.append(f"\\title{{{document.title}}}")
        
        # 作者
        if document.authors:
            lines.append(f"\\author{{{', '.join(document.authors)}}}")
        
        lines.append("\\date{\\today}")
        lines.append("")
        
        # 正文
        lines.append("\\begin{document}")
        lines.append("")
        lines.append("\\maketitle")
        lines.append("")
        
        # 章节
        for section in sorted(document.sections, key=lambda s: s.order):
            if section.level == 1:
                lines.append(f"\\section{{{section.title}}}")
            elif section.level == 2:
                lines.append(f"\\subsection{{{section.title}}}")
            else:
                lines.append(f"\\subsubsection{{{section.title}}}")
            
            lines.append("")
            
            if section.content:
                lines.append(section.content)
                lines.append("")
        
        # 参考文献
        if document.references:
            lines.append("\\begin{thebibliography}{99}")
            for i, ref in enumerate(document.references, 1):
                lines.append(f"\\bibitem{{ref{i}}} {ref.get('text', '')}")
            lines.append("\\end{thebibliography}")
        
        lines.append("")
        lines.append("\\end{document}")
        
        return "\n".join(lines)
    
    def _to_html(self, document: Document) -> str:
        """转换为HTML格式"""
        lines = []
        
        lines.append("<!DOCTYPE html>")
        lines.append("<html>")
        lines.append("<head>")
        lines.append(f"<title>{document.title}</title>")
        lines.append("<meta charset=\"UTF-8\">")
        lines.append("</head>")
        lines.append("<body>")
        lines.append("")
        
        # 标题
        lines.append(f"<h1>{document.title}</h1>")
        
        # 作者
        if document.authors:
            lines.append(f"<p><strong>Authors:</strong> {', '.join(document.authors)}</p>")
        
        # 章节
        for section in sorted(document.sections, key=lambda s: s.order):
            level = min(section.level + 1, 6)
            lines.append(f"<h{level}>{section.title}</h{level}>")
            
            if section.content:
                paragraphs = section.content.split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        lines.append(f"<p>{para.strip()}</p>")
        
        # 参考文献
        if document.references:
            lines.append("<h2>References</h2>")
            lines.append("<ol>")
            for ref in document.references:
                lines.append(f"<li>{ref.get('text', '')}</li>")
            lines.append("</ol>")
        
        lines.append("</body>")
        lines.append("</html>")
        
        return "\n".join(lines)
    
    def _to_plain_text(self, document: Document) -> str:
        """转换为纯文本格式"""
        lines = []
        
        # 标题
        lines.append(document.title)
        lines.append("=" * len(document.title))
        lines.append("")
        
        # 作者
        if document.authors:
            lines.append(f"Authors: {', '.join(document.authors)}")
            lines.append("")
        
        # 章节
        for section in sorted(document.sections, key=lambda s: s.order):
            lines.append(section.title)
            lines.append("-" * len(section.title))
            lines.append("")
            
            if section.content:
                lines.append(section.content)
                lines.append("")
        
        # 参考文献
        if document.references:
            lines.append("References")
            lines.append("----------")
            for i, ref in enumerate(document.references, 1):
                lines.append(f"{i}. {ref.get('text', '')}")
        
        return "\n".join(lines)
    
    async def generate_content(
        self,
        topic: str,
        content_type: str = "paragraph",
        style: str = "academic",
        length: str = "medium",
    ) -> Dict[str, Any]:
        """
        生成内容
        
        Args:
            topic: 主题
            content_type: 内容类型
            style: 写作风格
            length: 长度
            
        Returns:
            Dict[str, Any]: 生成结果
        """
        self._logger.info(f"Generating content for topic: {topic}")
        
        # 长度映射
        length_map = {
            "short": "100-200词",
            "medium": "300-500词",
            "long": "600-1000词",
        }
        
        # 内容类型映射
        type_map = {
            "paragraph": "一个完整的段落",
            "introduction": "引言部分",
            "conclusion": "结论部分",
            "abstract": "摘要",
            "literature_review": "文献综述",
            "methodology": "方法论描述",
        }
        
        prompt = f"""
        请为以下主题生成学术内容：
        
        主题：{topic}
        内容类型：{type_map.get(content_type, content_type)}
        风格：{style}
        长度：{length_map.get(length, length)}
        
        请确保内容：
        1. 符合学术写作规范
        2. 逻辑清晰，结构完整
        3. 使用适当的学术语言
        4. 包含必要的论据和支持
        
        请直接输出生成的内容。
        """
        
        content = await self.llm_service.generate(prompt)
        
        return {
            "topic": topic,
            "content_type": content_type,
            "style": style,
            "length": length,
            "content": content,
            "word_count": len(content.split()),
        }
    
    async def summarize_text(
        self,
        text: str,
        max_length: int = 200,
    ) -> Dict[str, Any]:
        """
        总结文本
        
        Args:
            text: 文本内容
            max_length: 最大长度
            
        Returns:
            Dict[str, Any]: 总结结果
        """
        self._logger.info(f"Summarizing text (max length: {max_length})")
        
        prompt = f"""
        请总结以下文本，控制在{max_length}词以内：
        
        {text}
        
        请确保总结：
        1. 保留主要观点和关键信息
        2. 语言简洁明了
        3. 逻辑连贯
        
        请直接输出总结内容。
        """
        
        summary = await self.llm_service.generate(prompt)
        
        return {
            "original_length": len(text.split()),
            "summary_length": len(summary.split()),
            "summary": summary,
            "compression_ratio": len(summary.split()) / len(text.split()) if text else 0,
        }
    
    async def translate_text(
        self,
        text: str,
        target_language: str = "en",
        source_language: str = "auto",
    ) -> Dict[str, Any]:
        """
        翻译文本
        
        Args:
            text: 文本内容
            target_language: 目标语言
            source_language: 源语言
            
        Returns:
            Dict[str, Any]: 翻译结果
        """
        self._logger.info(f"Translating text to {target_language}")
        
        # 语言映射
        language_map = {
            "en": "English",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
        }
        
        target_lang = language_map.get(target_language, target_language)
        
        prompt = f"""
        请将以下文本翻译成{target_lang}：
        
        {text}
        
        请确保翻译：
        1. 准确传达原意
        2. 符合目标语言的表达习惯
        3. 保持学术语言的正式性
        4. 专业术语翻译准确
        
        请直接输出翻译结果。
        """
        
        translated = await self.llm_service.generate(prompt)
        
        return {
            "source_language": source_language,
            "target_language": target_language,
            "original_text": text,
            "translated_text": translated,
            "original_length": len(text.split()),
            "translated_length": len(translated.split()),
        }
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """
        获取文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            Optional[Document]: 文档对象
        """
        return self._documents.get(document_id)
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        列出所有文档
        
        Returns:
            List[Dict[str, Any]]: 文档列表
        """
        documents = []
        for doc_id, doc in self._documents.items():
            documents.append({
                "id": doc_id,
                "title": doc.title,
                "authors": doc.authors,
                "word_count": doc.word_count,
                "status": doc.status,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
            })
        
        return documents
    
    def delete_document(self, document_id: str) -> bool:
        """
        删除文档
        
        Args:
            document_id: 文档ID
            
        Returns:
            bool: 是否成功删除
        """
        if document_id in self._documents:
            del self._documents[document_id]
            self._logger.info(f"Document {document_id} deleted")
            return True
        return False
    
    def get_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有模板
        
        Returns:
            Dict[str, Dict[str, Any]]: 模板字典
        """
        return self._templates
    
    def add_template(self, name: str, template: Dict[str, Any]) -> None:
        """
        添加模板
        
        Args:
            name: 模板名称
            template: 模板数据
        """
        self._templates[name] = template
        self._logger.info(f"Template added: {name}")