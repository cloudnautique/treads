import logging
import json
from datetime import datetime

from fastapi import HTTPException, Body, Request, APIRouter
from fastapi.responses import HTMLResponse

from treads.nanobot.client import NanobotClient
from treads.api.helper import (
    prefers_json,
    create_error_response,
    create_success_response,
    extract_prompt_from_body,
    extract_text_response_from_tool_result,
    extract_text_from_prompt_result,
    extract_text_from_resource_result,
    extract_arguments_from_body,
    fetch_and_render_ui_resource,  # NEW
)

logger = logging.getLogger(__name__)

TreadRouter = APIRouter()


@TreadRouter.post("/api/resources/ui")
async def get_ui_resource_endpoint(request: Request, body: dict = Body(...)):
    """
    FastAPI endpoint for fetching UI resources.
    Only supports 'ui://' URIs and returns the htmlString from the resource content.
    Always returns HTML content.
    """
    uri = body.get("uri")
    if not uri:
        raise HTTPException(status_code=400, detail="Missing 'uri' parameter")
    return await fetch_and_render_ui_resource(uri)


@TreadRouter.get("/api/{agent}/templates")
async def list_agent_resource_templates(request: Request, agent: str):
    """
    Lists all resource templates for a specific agent (including UI templates).
    Returns htmlString or JSON with a list of templates.
    """
    prefer_json = prefers_json(request)
    try:
        async with NanobotClient() as client:
            templates_raw = await client.list_resource_templates()
            templates = [t.model_dump() for t in templates_raw]
        context = {"templates": templates, "agent": agent}
        html = await fetch_and_render_ui_resource(f"ui://{agent}/resource_templates", context)
        return create_success_response(
            {"templates": templates, "agent": agent},
            prefer_json,
            html
        )
    except Exception as e:
        logger.error(f"Error listing resource templates for agent '{agent}': {e}")
        return create_error_response(str(e), prefer_json, "<div>err</div>", agent=agent)


@TreadRouter.get("/api/{agent}/templates/{name}")
async def get_agent_resource_template(request: Request, agent: str, name: str):
    """
    Retrieves a specific resource template by name for an agent.
    Returns the template content as HTML or JSON.
    """
    prefer_json = prefers_json(request)
    try:
        async with NanobotClient() as client:
            templates = await client.list_resource_templates()
            template = next((t for t in templates if t.name == name), None)
        if template:
            html = await fetch_and_render_ui_resource(f"ui://{agent}/resource_templates/{name}/form")
            return create_success_response(
                {"template": template.model_dump()},
                prefer_json,
                html
            )
        else:
            raise HTTPException(status_code=404, detail=f"Template '{name}' not found for agent '{agent}'")
    except Exception as e:
        logger.error(f"Error retrieving template '{name}' for agent '{agent}': {e}")
        return create_error_response(str(e), prefer_json, "<div>err</div>", agent=agent, template_name=name)


@TreadRouter.get("/api/{agent}/prompts")
async def list_agent_prompts(request: Request, agent: str):
    """
    Lists prompts for a specific agent.
    Returns htmlString or JSON with a list of prompts.
    """
    prefer_json = prefers_json(request)
    try:
        async with NanobotClient() as client:
            prompts_raw = await client.list_prompts()
            prompts = [prompt.model_dump() for prompt in prompts_raw]
        context = {"prompts": prompts, "agent": agent}
        html = await fetch_and_render_ui_resource(f"ui://{agent}/prompts", context)
        return create_success_response(
            {"prompts": prompts, "agent": agent},
            prefer_json,
            html
        )
    except Exception as e:
        logger.error(f"Error listing prompts for agent '{agent}': {e}")
        return create_error_response(str(e), prefer_json, "<div>err</div>", agent=agent)


@TreadRouter.get("/api/{agent}/prompts/{name}")
async def get_agent_prompt(request: Request, agent: str, name: str):
    """
    Retrieves a specific prompt by name for an agent.
    Returns the prompt content as HTML or JSON.
    """
    prefer_json = prefers_json(request)
    try:
        async with NanobotClient() as client:
            prompts = await client.list_prompts()
            prompt = next((p for p in prompts if p.name == name), None)
        if prompt:
            context = {"prompt": prompt}
            html = await fetch_and_render_ui_resource(f"ui://{agent}/prompts/{name}/form", context)
            return create_success_response(
                {"prompt": prompt.model_dump()},
                prefer_json,
                html
            )
        else:
            raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found for agent '{agent}'")   
    except Exception as e:
        logger.error(f"Error retrieving prompt '{name}' for agent '{agent}': {e}")
        return create_error_response(str(e), prefer_json, "<div>err</div>", agent=agent, prompt_name=name)


@TreadRouter.post("/api/{agent}/invoke")
async def invoke_agent(request: Request, agent: str, body: dict = Body(...)):
    """
    Invokes an agent with a prompt and returns a customizable response.
    Uses agent-specific view snippets from ui://{agent}/chat_response if available.
    Implements fallback: tries response_type, then chat_response, then generic fallback.
    Adds debug logging for troubleshooting.
    """
    logger.info(f"Invoking agent '{agent}' with prompt")
    logger.debug(f"Request body: {body}")
    
    # Extract prompt using helper function
    try:
        prompt = extract_prompt_from_body(body)
    except Exception as e:
        logger.error(f"Failed to extract prompt from body: {body}, error: {e}")
        raise
    logger.debug(f"Extracted prompt: {prompt}")
    prefer_json = prefers_json(request)
    
    try:
        async with NanobotClient() as client:
            result = await client.call_tool(agent, {"prompt": prompt})
            logger.debug(f"Raw result from client.call_tool: {result}")
            response = extract_text_response_from_tool_result(result)
        
        logger.info(f"Extracted response: {response}")

        #try to parse response as JSON if it's a string
        if isinstance(response, str):
            try:
                response = json.loads(response)
                logger.info("Response parsed as JSON")
            except json.JSONDecodeError:
                logger.warning("Response is not valid JSON, using raw string")
                pass
        
        # Extract response_type from response if it's a dict, default to "chat_response"
        response_type = "chat_response"
        if isinstance(response, dict) and "response_type" in response:
            response_type = response["response_type"]
            # Remove response_type from the response data so it doesn't appear in the template
            response_data = {k: v for k, v in response.items() if k != "response_type"}
        else:
            response_data = response
        logger.info(f"response_type: {response_type}, response_data: {response_data}")

        # Handle structured data vs text for template rendering
        if isinstance(response_data, (dict, list)):
            response_formatted = json.dumps(response_data, indent=2)
            response_for_json = response_data
        else:
            response_formatted = str(response_data)
            response_for_json = response_data

        template_context = {
            "response": response_data,  # Raw structured data for template access
            "response_formatted": response_formatted,  # Pretty-printed version for display
            "agent": agent,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat(),
            "response_type": response_type  # Include response_type in context
        }
        logger.info(f"Template context for rendering: {template_context}")

        # --- Fallback logic for template rendering ---
        rendered_html = None
        tried_templates = [
            f"ui://{agent}/{response_type}",  # Try the actual response_type first
            f"ui://{agent}/chat_response"     # Then fallback to chat_response
        ]
        for uri in tried_templates:
            logger.info(f"Trying to render template: {uri}")
            try:
                rendered_html = await fetch_and_render_ui_resource(uri, template_context)
                logger.info(f"Successfully rendered template: {uri}")
                logger.info(f"Rendered HTML content: {rendered_html}")
                break
            except HTTPException as e:
                logger.warning(f"Template {uri} not found or error: {e}")
                if e.status_code != 404:
                    raise  # Only fallback on 404, not other errors
        if not rendered_html:
            logger.warning("Falling back to generic HTML response.")
            rendered_html = HTMLResponse(f"<div class='chat-bubble chat-bubble-bot'>Response: {response_formatted}</div>")
        # --- End fallback logic ---
        
        return create_success_response(
            {"response": response_for_json, "prompt": prompt, "agent": agent},
            prefer_json,
            rendered_html
        )
        
    except Exception as e:
        logger.error(f"Agent '{agent}' invocation failed: {e}", exc_info=True)
        return create_error_response(
            str(e), 
            prefer_json, 
            "<div class='text-red-500'>Error invoking agent</div>",
            prompt=prompt,
            agent=agent
        )


@TreadRouter.post("/api/{agent}/prompts/{name}/messages")
async def get_rendered_prompt_messages(request: Request, agent: str, name: str, body: dict = Body(...)):
    arguments = extract_arguments_from_body(body)
    prefer_json = prefers_json(request)

    logger.info(f"Fetching rendered messages for prompt '{name}' with arguments: {arguments}")
    
    try:
        async with NanobotClient() as client:
            result = await client.get_prompt(name, arguments=arguments)
            logger.info(f"Raw result from client.get_prompt: {result}")
            extracted_text = extract_text_from_prompt_result(result)
        
        return create_success_response(
            {"content": extracted_text, "prompt_name": name, "arguments": arguments},
            prefer_json,
            HTMLResponse(extracted_text)
        )
            
    except Exception as e:
        logger.error(f"Prompt rendered messages fetch failed: {e}")
        return create_error_response(str(e), prefer_json, prompt_name=name, arguments=arguments)


@TreadRouter.post("/api/{agent}/templates/messages")
async def get_resource_with_instructions(request: Request, agent: str, body: dict = Body(...)):
    """
    Accepts a URI directly in the request body along with optional user instructions.
    Retrieves the resource using the URI and sends it to the chat agent for a response.
    """
    uri = body.get("uri")
    instructions = body.get("instructions", "")
    prefer_json = prefers_json(request)
    
    if not uri:
        logger.error("Missing required 'uri' parameter")
        error_template = '<div class="chat-bubble chat-bubble-bot text-red-500">Missing required parameter: uri</div>'
        return create_error_response(
            "Missing required parameter: uri", 
            prefer_json, 
            error_template, 
            uri=None
        )
    
    try:
        logger.info(f"Fetching resource from URI: {uri}")
        
        async with NanobotClient() as client:
            result = await client.read_resource(uri=uri)
            logger.info(f"Resource result: {result}")
            
            # Extract text content from the resource
            extracted_content = extract_text_from_resource_result(result)
            
            if extracted_content:
                # Format the prompt for the chat agent
                prompt_text = f"Resource from {uri}:\n\n{extracted_content}"
                if instructions:
                    prompt_text += f"\n\nInstructions: {instructions}"
            else:
                # Return a generic message if we couldn't extract content
                return f"I'd like to know about the resource at {uri} {instructions}"
        
        return create_success_response(
            {"content": prompt_text, "uri": uri, "instructions": instructions},
            prefer_json,
            HTMLResponse(prompt_text)
        )
            
    except Exception as e:
        logger.error(f"Error processing resource request: {e}")
        error_template = '<div class="chat-bubble chat-bubble-bot text-red-500">Error retrieving resource: {error}</div>'
        return create_error_response(str(e), prefer_json, error_template, uri=uri, instructions=instructions)


__all__ = ["TreadRouter"]
