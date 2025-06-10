from treads.nanobot.client import NanobotClient


class PromptService:
    @staticmethod
    async def get_prompts():
        """Get all prompts, returning (list, dict) tuple."""
        async with NanobotClient() as client:
            prompts = await client.list_prompts() or []
        
        prompt_list = []
        prompts_dict = {}
        
        for prompt in prompts:
            name = prompt.name if hasattr(prompt, 'name') else None
            prompt_data = {
                "name": name,
                "description": prompt.description if hasattr(prompt, 'description') and prompt.description else "",
                "arguments": [arg.model_dump() for arg in prompt.arguments] if hasattr(prompt, 'arguments') and prompt.arguments else [],
            }
            prompt_list.append(prompt_data)
            if name:
                prompts_dict[name] = prompt
        
        return prompt_list, prompts_dict


class TemplateService:
    @staticmethod
    async def get_templates():
        """Get all resource templates, returning (list, dict) tuple."""
        async with NanobotClient() as client:
            templates = await client.list_resource_templates() or []
        
        template_list = []
        templates_dict = {}
        
        for template in templates:
            name = template.name if hasattr(template, 'name') else None
            template_data = {
                "name": name,
                "description": template.description if hasattr(template, 'description') and template.description else "",
                "arguments": [arg.model_dump() for arg in template.arguments] if hasattr(template, 'arguments') and template.arguments else [],
                "uriTemplate": template.uriTemplate if hasattr(template, 'uriTemplate') else None,
            }
            template_list.append(template_data)
            if name:
                templates_dict[name] = template
        
        return template_list, templates_dict
