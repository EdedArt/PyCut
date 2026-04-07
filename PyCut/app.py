import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from logic_list import DoublyLinkedListTimeline, THUMBNAILS_DIR
from moviepy import VideoFileClip, concatenate_videoclips
from moviepy.video.fx import BlackAndWhite
import shutil

# Storage Paths
UPLOADS_DIR = "c:/Users/labinf1.pasto/Downloads/PyCut/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)

app = FastAPI(title="FlowCut - Video Editor Prototype")
app.mount("/static", StaticFiles(directory="c:/Users/labinf1.pasto/Downloads/PyCut/static"), name="static")

# Global instance of the Doubly Linked List
timeline = DoublyLinkedListTimeline()

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("c:/Users/labinf1.pasto/Downloads/PyCut/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/timeline")
def get_timeline():
    return timeline.traverse_list()

@app.get("/api/file/{filename}")
def serve_file(filename: str):
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...), user_mode: bool = Body(False)):
    # Limit for Guest Mode
    if not user_mode and timeline.size >= 3:
        raise HTTPException(status_code=403, detail="Guest Mode: 3 clip limit reached. Sign in to unlock.")
        
    if not file.filename.endswith(('.mp4', '.mov', '.avi', '.mkv')):
        raise HTTPException(status_code=400, detail="File format not supported.")

    file_path = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    node = timeline.insert_at_end(file_path)
    if node is None:
        raise HTTPException(status_code=500, detail="Error processing video with MoviePy.")
        
    return {"message": "Video uploaded and inserted into timeline."}

@app.post("/api/move")
def move_clip(node_id: str = Body(...), direction: str = Body(...)):
    success = timeline.move_position(node_id, direction)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid movement (reached limits).")
    return {"message": "Clip moved successfully."}

@app.delete("/api/delete/{node_id}")
def delete_clip(node_id: str):
    success = timeline.remove_clip(node_id)
    if not success:
        raise HTTPException(status_code=404, detail="Clip not found.")
    return {"message": "Clip deleted."}

@app.post("/api/toggle_filter")
def toggle_filter(node_id: str = Body(...), user_mode: bool = Body(False)):
    if not user_mode:
        raise HTTPException(status_code=403, detail="You must be a User to apply filters.")
        
    node = timeline.find_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Clip not found.")
    
    node.grayscale_filter = not node.grayscale_filter
    return {"message": "Filter toggled."}

@app.post("/api/trim")
def trim_clip(node_id: str = Body(...), start: float = Body(...), end: float = Body(...), user_mode: bool = Body(False)):
    if not user_mode:
        raise HTTPException(status_code=403, detail="You must be a User to Trim videos.")
        
    success = timeline.trim_node(node_id, start, end)
    if not success:
        raise HTTPException(status_code=400, detail="Error trimming clip (Invalid times or node not found).")
    return {"message": "Clip trimmed."}

@app.post("/api/split")
def split_clip(node_id: str = Body(...), split_time: float = Body(...), user_mode: bool = Body(False)):
    if not user_mode:
        raise HTTPException(status_code=403, detail="You must be a User to Split videos.")
    
    success = timeline.split_node(node_id, split_time)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid split time or node not found.")
    return {"message": "Clip split in two perfectly using Doubly Linked List node injection."}

@app.post("/api/render")
def render_video(user_mode: bool = Body(False)):
    if not user_mode:
        raise HTTPException(status_code=403, detail="You must be a User to Render the final video.")
    
    if timeline.size == 0:
        raise HTTPException(status_code=400, detail="Timeline is empty.")
        
    try:
        clips = []
        current = timeline.head
        while current:
            # Load clip and apply exact Subclip based on Trim/Split features
            v_clip = VideoFileClip(current.file_path).subclipped(current.trim_start, current.trim_end)
            
            # Apply filter if activated
            if current.grayscale_filter:
                # Black and white filter
                v_clip = v_clip.with_effects([BlackAndWhite()])
                
            clips.append(v_clip)
            current = current.next
            
        final_clip = concatenate_videoclips(clips, method="compose")
        output_path = "c:/Users/labinf1.pasto/Downloads/PyCut/static/output.mp4"
        
        # Save low res for prototype speed
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
        
        # Release memory
        for clip in clips:
            clip.close()
        final_clip.close()
        
        return {"url": "/static/output.mp4"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering video: {e}")
