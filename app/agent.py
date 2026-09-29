# ruff: noqa
# Copyright 2026 Google LLC

import base64
import datetime
import json
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import client, types

from app.a2ui_utils import a2ui_callback

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-02-2a28910a07ed"
GCS_BUCKET_NAME = "travel-concierge-media-qwiklabs-gcp-02-2a28910a07ed"


def _get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded project ID."""
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each turn, extract durable snippets and add session to Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


def generate_destination_image(
    prompt: str, tool_context: ToolContext = None
) -> str:
    """Generate a photo or visual preview for a travel destination or landmark.

    Args:
        prompt: Detailed text description of the image to generate.
        tool_context: Context provided automatically by the ADK runtime.

    Returns:
        The public HTTPS URL of the generated image hosted on Cloud Storage.
    """
    if not prompt:
        return "Please provide a prompt for image generation."

    try:
        # Generate image using gemini-3.1-flash-lite-image in global region
        ai_client = client.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT_ID,
            location="global",
        )
        response = ai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return f"Failed to generate image bytes for prompt: '{prompt}'."

        timestamp = int(datetime.datetime.now().timestamp())
        ext = "png" if "png" in mime_type else "jpg"
        filename = f"destination_{timestamp}.{ext}"

        # 1. Save artifact in Playground's Artifacts panel using tool_context
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                tool_context.save_artifact(
                    filename=filename,
                    contents=image_bytes,
                    mime_type=mime_type,
                )
            except Exception as artifact_err:
                print(f"Warning saving artifact: {artifact_err}")

        # 2. Upload image bytes directly to the public GCS bucket
        gcs_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = gcs_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"images/{filename}")
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/images/{filename}"
        return (
            f"Successfully generated destination image!\n"
            f"Public HTTPS URL: {public_url}"
        )
    except Exception as e:
        return f"Error generating image: {str(e)}"


def generate_destination_video(
    prompt: str, tool_context: ToolContext = None
) -> str:
    """Generate a short video clip or preview for a travel destination or landmark using Google's Omni model (gemini-omni-flash-preview).

    Args:
        prompt: Detailed text description of the travel video to generate.
        tool_context: Context provided automatically by the ADK runtime.

    Returns:
        The public HTTPS URL of the generated video hosted on Cloud Storage.
    """
    if not prompt:
        return "Please provide a prompt for video generation."

    try:
        # Generate video using gemini-omni-flash-preview in global region
        ai_client = client.Client(
            vertexai=True,
            project=FIRESTORE_PROJECT_ID,
            location="global",
        )
        response = ai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_modalities=["text", "video"],
        )

        video_bytes = None
        mime_type = "video/mp4"

        if hasattr(response, "output_video") and response.output_video:
            raw_data = response.output_video.data
            mime_type = getattr(response.output_video, "mime_type", None) or "video/mp4"
            if isinstance(raw_data, str):
                try:
                    video_bytes = base64.b64decode(raw_data)
                except Exception:
                    video_bytes = raw_data.encode("utf-8")
            elif isinstance(raw_data, bytes):
                video_bytes = raw_data

        if not video_bytes and hasattr(response, "steps") and response.steps:
            for step in response.steps:
                content_list = getattr(step, "content", []) or []
                for content in content_list:
                    if getattr(content, "type", "") == "video" or hasattr(content, "data"):
                        raw_data = getattr(content, "data", None)
                        mime_type = getattr(content, "mime_type", None) or "video/mp4"
                        if isinstance(raw_data, str):
                            try:
                                video_bytes = base64.b64decode(raw_data)
                            except Exception:
                                video_bytes = raw_data.encode("utf-8")
                        elif isinstance(raw_data, bytes):
                            video_bytes = raw_data
                        if video_bytes:
                            break

        if not video_bytes:
            return f"Failed to generate video bytes for prompt: '{prompt}'."

        timestamp = int(datetime.datetime.now().timestamp())
        ext = "mp4" if "mp4" in mime_type else "mp4"
        filename = f"destination_video_{timestamp}.{ext}"

        # 1. Save artifact in Playground's Artifacts panel using tool_context
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                tool_context.save_artifact(
                    filename=filename,
                    contents=video_bytes,
                    mime_type=mime_type,
                )
            except Exception as artifact_err:
                print(f"Warning saving artifact: {artifact_err}")

        # 2. Upload video bytes directly to the public GCS bucket (no local file writing)
        gcs_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = gcs_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"videos/{filename}")
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/videos/{filename}"
        return (
            f"Successfully generated destination video!\n"
            f"Public HTTPS URL: {public_url}"
        )
    except Exception as e:
        return f"Error generating video: {str(e)}"


def get_live_weather(city: str) -> str:
    """Fetch live real-time weather information for any city worldwide.

    Args:
        city: Name of the city to look up weather for (e.g. 'Kyoto', 'Paris', 'San Francisco').

    Returns:
        A string containing current temperature, condition, humidity, and feels-like temperature.
    """
    if not city:
        return "Please provide a valid city name."

    try:
        encoded_city = urllib.parse.quote(city.strip())
        url = f"https://wttr.in/{encoded_city}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        current = data["current_condition"][0]
        temp_c = current.get("temp_C")
        temp_f = current.get("temp_F")
        desc = current.get("weatherDesc", [{}])[0].get("value", "Unknown condition")
        feels_c = current.get("FeelsLikeC")
        humidity = current.get("humidity")

        return (
            f"Current weather in {city.title()}: {desc}, {temp_c}°C ({temp_f}°F). "
            f"Feels like {feels_c}°C, humidity {humidity}%."
        )
    except Exception as e:
        return f"Could not fetch live weather for '{city}': {e}."


def search_destinations(city: str = "", category: str = "") -> str:
    """Search travel destinations from the Firestore catalog.

    Args:
        city: Optional city name to filter by (e.g. 'Kyoto', 'San Francisco', 'Paris').
        category: Optional category to filter by (e.g. 'Culture & History', 'Art & History').

    Returns:
        A string listing matching destinations found in the database.
    """
    db = _get_firestore_client()
    query_ref = db.collection("destinations")
    docs = query_ref.stream()

    results = []
    city_lower = city.strip().lower()
    category_lower = category.strip().lower()

    for doc in docs:
        data = doc.to_dict()
        doc_city = data.get("city", "").lower()
        doc_category = data.get("category", "").lower()

        if city_lower and city_lower not in doc_city:
            continue
        if category_lower and category_lower not in doc_category:
            continue

        results.append(data)

    if not results:
        return f"No destinations found matching city='{city}' and category='{category}'."

    summary_lines = []
    for d in results:
        summary_lines.append(
            f"• {d.get('name')} ({d.get('city')}, {d.get('country')}) [{d.get('category')}]\n"
            f"  Description: {d.get('description')}\n"
            f"  Avg Rating: {d.get('average_rating')} | Est. Cost: ${d.get('estimated_cost_usd', 0.0):.2f}\n"
            f"  Tags: {', '.join(d.get('tags', []))}"
        )

    return "\n\n".join(summary_lines)


def add_destination(
    name: str,
    city: str,
    country: str,
    category: str,
    description: str,
    estimated_cost_usd: float = 0.0,
    tags: str = "",
) -> str:
    """Add a new travel destination to the Firestore catalog.

    Args:
        name: Name of the destination/attraction.
        city: City where it is located.
        country: Country where it is located.
        category: Category of attraction (e.g., 'Sightseeing', 'Food & Dining').
        description: A brief summary description.
        estimated_cost_usd: Estimated cost in USD.
        tags: Comma-separated list of descriptive tags.

    Returns:
        A success message with the created destination ID.
    """
    db = _get_firestore_client()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    doc_id = f"dest_{int(datetime.datetime.now().timestamp())}"
    doc_data = {
        "id": doc_id,
        "name": name,
        "city": city,
        "country": country,
        "category": category,
        "description": description,
        "average_rating": 5.0,
        "estimated_cost_usd": float(estimated_cost_usd),
        "tags": tag_list,
    }

    db.collection("destinations").document(doc_id).set(doc_data)
    return f"Successfully added destination '{name}' to {city}, {country} with ID {doc_id}."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    elif "paris" in query.lower():
        tz_identifier = "Europe/Paris"
    elif "tokyo" in query.lower() or "kyoto" in query.lower():
        tz_identifier = "Asia/Tokyo"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Build A2UI system prompt using version 0.8 and BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description="You are a helpful Travel Concierge and Local Guide AI assistant.",
    workflow_description="Analyze the user request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        generate_destination_image,
        generate_destination_video,
        search_destinations,
        add_destination,
        get_live_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
