from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class HTMLTextType(BaseModel):
    """Pydantic model to represent HTML text type for content delivery."""
    html_string: str = Field(..., alias="htmlString")

    def to_dict(self) -> Dict[str, Any]:
        return {"content": {"type": "rawHtml", "HTMLString": self.html_string}}

class HTMLTemplate(BaseModel):
    """Pydantic model to represent template content for MCP resources."""
    template_content: str = Field(..., alias="htmlTemplateString")
    context_schema: Optional[Any] = Field(default_factory=dict, alias="contextSchema")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": {
                "type": "htmlTemplate",
                "htmlTemplateString": self.template_content,
                "contextSchema": self.context_schema
            }
        }

class HTMLExternalType(BaseModel):
    """Pydantic model to represent external HTML content."""
    iframeUrl: str = Field(..., alias="iframeUrl")
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": {
                "type": "externalUrl",
                "iframeUrl": self.iframeUrl
            }
        }