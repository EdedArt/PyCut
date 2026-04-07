import uuid
import os
from moviepy import VideoFileClip

# Folder to store generated thumbnails
THUMBNAILS_DIR = "c:/Users/labinf1.pasto/Downloads/PyCut/static/thumbnails"
os.makedirs(THUMBNAILS_DIR, exist_ok=True)

class ClipNode:
    """Node representing a video clip in the doubly linked list."""
    def __init__(self, node_id, file_path, duration, thumbnail, trim_start=0.0, trim_end=None):
        self.id = node_id
        self.file_path = file_path
        self.duration = duration
        self.trim_start = trim_start
        self.trim_end = trim_end if trim_end is not None else duration
        
        self.thumbnail = thumbnail
        self.grayscale_filter = False # For the filter option
        
        self.next = None
        self.prev = None

class DoublyLinkedListTimeline:
    """Timeline implementation as a Doubly Linked List."""
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def insert_at_end(self, file_path: str):
        """If video is valid, extracts duration and thumbnail and creates node at the end."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} does not exist.")
        
        try:
            # MoviePy usage to generate metadata and thumbnail
            with VideoFileClip(file_path) as clip:
                duration = clip.duration
                node_id = str(uuid.uuid4())
                thumbnail_filename = f"thumb_{node_id}.jpg"
                thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_filename)
                
                # Save frame at the first 0.5s or start
                t_frame = min(0.5, duration * 0.1)
                clip.save_frame(thumbnail_path, t=t_frame)
                
                thumbnail_url = f"/static/thumbnails/{thumbnail_filename}"
        except Exception as e:
            print(f"Error processing video with moviepy: {e}")
            return None

        # Node creation after moviepy validation
        new_node = ClipNode(node_id, file_path, duration, thumbnail_url)
        
        if self.head is None:
            self.head = new_node
            self.tail = new_node
        else:
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node
            
        self.size += 1
        return new_node
        
    def find_node(self, node_id: str):
        """Finds and returns a node by its id."""
        current = self.head
        while current:
            if current.id == node_id:
                return current
            current = current.next
        return None

    def remove_clip(self, node_id: str):
        """Removes a node from the list decoupling pointers."""
        node = self.find_node(node_id)
        if not node:
            return False
            
        if node.prev:
            node.prev.next = node.next
        else:
            self.head = node.next
            
        if node.next:
            node.next.prev = node.prev
        else:
            self.tail = node.prev
            
        self.size -= 1
        
        # Remove thumbnail file to keep space clean
        try:
            thumb_path = node.thumbnail.replace('/static/thumbnails/', THUMBNAILS_DIR + '/')
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        except:
            pass
            
        return True

    def move_position(self, node_id: str, direction: str):
        """
        Moves clip 'left' (prev) or 'right' (next).
        Swaps positions modifying pointers temporarily.
        """
        node = self.find_node(node_id)
        if not node:
            return False
            
        if direction == "left" and node.prev:
            node1 = node.prev
            node2 = node
        elif direction == "right" and node.next:
            node1 = node
            node2 = node.next
        else:
            return False # Cannot be moved

        # Swap node1 and node2 (adjacent nodes)
        prev1 = node1.prev
        next2 = node2.next
        
        node2.next = node1
        node1.prev = node2
        
        node2.prev = prev1
        if prev1:
            prev1.next = node2
        else:
            self.head = node2
            
        node1.next = next2
        if next2:
            next2.prev = node1
        else:
            self.tail = node1
            
        return True

    def trim_node(self, node_id: str, start: float, end: float):
        """Updates the trim times for a given node."""
        node = self.find_node(node_id)
        if not node: return False
        
        # Validation
        if start < 0 or start >= node.duration: start = 0.0
        if end <= start or end > node.duration: end = node.duration
        
        node.trim_start = float(start)
        node.trim_end = float(end)
        return True

    def split_node(self, node_id: str, split_time: float):
        """
        Doubly Linked List operation: Splits one node in two.
        Clones the node, assigns one the first half of the time limit,
        the clone gets the second half, and inserts the clone AFTER the current node.
        """
        node = self.find_node(node_id)
        if not node: return False
        
        if split_time <= node.trim_start or split_time >= node.trim_end:
            return False # Invalid split point

        # Create new_node cloned properties
        clone_id = str(uuid.uuid4())
        new_node = ClipNode(
            node_id=clone_id, 
            file_path=node.file_path, 
            duration=node.duration, 
            thumbnail=node.thumbnail,
            trim_start=split_time, 
            trim_end=node.trim_end
        )
        new_node.grayscale_filter = node.grayscale_filter

        # Update current node's end time to the split boundary
        node.trim_end = split_time

        # THE DOUBLY LINKED LIST INJECTION (node -> new_node -> node.next):
        old_next = node.next
        
        node.next = new_node
        new_node.prev = node
        new_node.next = old_next
        
        if old_next:
            old_next.prev = new_node
        else:
            self.tail = new_node # new_node is the new tail
            
        self.size += 1
        return True

    def traverse_list(self):
        """Traverses the doubly linked list returning sequence array state."""
        result = []
        current = self.head
        while current:
            result.append({
                "id": current.id,
                "file_path": current.file_path,
                "duration": round(current.duration, 2),
                "thumbnail": current.thumbnail,
                "grayscale_filter": current.grayscale_filter,
                "trim_start": round(current.trim_start, 2),
                "trim_end": round(current.trim_end, 2)
            })
            current = current.next
        return result
