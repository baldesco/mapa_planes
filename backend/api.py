from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Query
from typing import Optional, List
from backend import db, models, utils

app = FastAPI()

@app.post("/api/places/", response_model=models.Place, status_code=201)
async def create_place(place: models.PlaceCreate):
    conn, cursor = db.get_db()
    try:
        cursor.execute(
            "INSERT INTO places (name, category, latitude, longitude) VALUES (%s, %s, %s, %s) RETURNING id, status",
            (place.name, place.category, place.latitude, place.longitude),
        )
        place_id, status = cursor.fetchone()
        conn.commit()
        return models.Place(**place.dict(), id=place_id, status=status)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close_db(conn, cursor)

@app.put("/api/places/{place_id}", response_model=models.Place)
async def update_place_status(place_id: int, status: str):
    if status not in ["visited", "pending", "prioritized"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    conn, cursor = db.get_db()
    try:
        cursor.execute("UPDATE places SET status = %s WHERE id = %s RETURNING id, name, category, latitude, longitude, status", (status, place_id))
        result = cursor.fetchone()
        conn.commit()
        if result:
            return models.Place(id=result[0], name=result[1], category=result[2], latitude=result[3], longitude=result[4], status=result[5])
        else:
            raise HTTPException(status_code=404, detail="Place not found")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close_db(conn, cursor)

@app.post("/api/places/{place_id}/review", response_model=models.Review, status_code=201)
async def add_review(place_id: int, review_text: Optional[str] = Form(None), image: Optional[UploadFile] = File(None)):
    conn, cursor = db.get_db()
    image_path = None
    try:
        image_path = await utils.save_image(place_id, image)

        cursor.execute(
            "INSERT INTO reviews (place_id, review_text, image_path) VALUES (%s, %s, %s) RETURNING id, place_id, review_text, image_path",
            (place_id, review_text, image_path),
        )
        review_id, place_id_db, review_text_db, image_path_db = cursor.fetchone()
        conn.commit()
        return models.Review(id=review_id, place_id=place_id_db, review_text=review_text_db, image_path=image_path_db)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close_db(conn, cursor)

@app.get("/api/places/", response_model=List[models.Place])
async def get_places(category: Optional[str] = Query(None), status: Optional[str] = Query(None)):
    conn, cursor = db.get_db()
    try:
        query = "SELECT id, name, category, latitude, longitude, status FROM places WHERE 1=1"
        params = []
        if category:
            query += " AND category = %s"
            params.append(category)
        if status:
            query += " AND status = %s"
            params.append(status)
        cursor.execute(query, params)
        results = cursor.fetchall()
        places = [models.Place(id=row[0], name=row[1], category=row[2], latitude=row[3], longitude=row[4], status=row[5]) for row in results]
        return places
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close_db(conn, cursor)

@app.get("/api/places/{place_id}", response_model=models.Place)
async def get_place_details(place_id: int):
    conn, cursor = db.get_db()
    try:
        cursor.execute("SELECT id, name, category, latitude, longitude, status FROM places WHERE id = %s", (place_id,))
        place_result = cursor.fetchone()
        if not place_result:
            raise HTTPException(status_code=404, detail="Place not found")
        place = models.Place(id=place_result[0], name=place_result[1], category=place_result[2], latitude=place_result[3], longitude=place_result[4], status=place_result[5])

        cursor.execute("SELECT id, review_text, image_path, place_id FROM reviews WHERE place_id = %s", (place_id,))
        review_results = cursor.fetchall()
        reviews = [models.Review(id=row[0], review_text=row[1], image_path=row[2], place_id=row[3]) for row in review_results]

        place_data = place.dict()
        place_data["reviews"] = reviews
        return place_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close_db(conn, cursor)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)