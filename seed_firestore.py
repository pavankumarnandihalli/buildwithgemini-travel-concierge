"""Seed script for initializing the Firestore 'destinations' collection."""

from google.cloud import firestore

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-02-2a28910a07ed"

SEED_DESTINATIONS = [
    {
        "id": "dest_001",
        "name": "Fushimi Inari Shrine",
        "city": "Kyoto",
        "country": "Japan",
        "category": "Culture & History",
        "description": "Iconic Shinto shrine famous for thousands of vibrant vermilion torii gates winding up Mount Inari.",
        "average_rating": 4.9,
        "estimated_cost_usd": 0.0,
        "tags": ["historic", "shrine", "temples", "scenic"],
    },
    {
        "id": "dest_002",
        "name": "Golden Gate Bridge & Park",
        "city": "San Francisco",
        "country": "USA",
        "category": "Sightseeing & Nature",
        "description": "World-famous suspension bridge paired with a massive 1,000-acre urban park featuring gardens and ocean views.",
        "average_rating": 4.8,
        "estimated_cost_usd": 15.0,
        "tags": ["landmark", "outdoors", "scenic", "iconic"],
    },
    {
        "id": "dest_003",
        "name": "Louvre Museum & Tuileries Garden",
        "city": "Paris",
        "country": "France",
        "category": "Art & History",
        "description": "The world's largest art museum housing masterpieces like Mona Lisa, surrounded by historic royal gardens.",
        "average_rating": 4.8,
        "estimated_cost_usd": 25.0,
        "tags": ["museum", "art", "culture", "landmark"],
    },
    {
        "id": "dest_004",
        "name": "Colosseum & Roman Forum",
        "city": "Rome",
        "country": "Italy",
        "category": "History & Archaeology",
        "description": "Ancient Roman amphitheater and administrative ruins in the heart of Rome.",
        "average_rating": 4.9,
        "estimated_cost_usd": 30.0,
        "tags": ["ancient", "history", "archeology", "architecture"],
    },
    {
        "id": "dest_005",
        "name": "Sagrada Família",
        "city": "Barcelona",
        "country": "Spain",
        "category": "Architecture & Art",
        "description": "Gaudí's unfinished masterpiece cathedral, renowned for organic modernist architecture and stained glass.",
        "average_rating": 4.9,
        "estimated_cost_usd": 35.0,
        "tags": ["architecture", "cathedral", "gaudi", "iconic"],
    },
]


def seed_database():
    print(f"Connecting to Firestore with project ID: {FIRESTORE_PROJECT_ID}...")
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    collection_ref = db.collection("destinations")

    for item in SEED_DESTINATIONS:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"Seeded destination: {item['name']} ({item['city']})")

    print(f"Successfully seeded {len(SEED_DESTINATIONS)} items to 'destinations' collection.")


if __name__ == "__main__":
    seed_database()
