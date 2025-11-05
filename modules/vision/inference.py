"""
YOLO Inference Pipeline for Construction Site Safety Detection
"""
import argparse
from pathlib import Path
from ultralytics import YOLO
import cv2
import numpy as np


class SafetyDetector:
    """YOLO-based safety detection for construction sites"""
    
    def __init__(self, model_path: str, conf_threshold: float = 0.25, iou_threshold: float = 0.7):
        """
        Initialize the safety detector
        
        Args:
            model_path: Path to the YOLO model weights (.pt file)
            conf_threshold: Confidence threshold for detections
            iou_threshold: IOU threshold for NMS
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # Get class names from the model
        self.class_names = self.model.names
        print(f"Model loaded with {len(self.class_names)} classes:")
        for idx, name in self.class_names.items():
            print(f"  {idx}: {name}")
        
    def predict_image(self, image_path: str, save_path: str = None, show: bool = False):
        """
        Run inference on a single image
        
        Args:
            image_path: Path to input image
            save_path: Path to save annotated image (optional)
            show: Whether to display the result
            
        Returns:
            Results object from YOLO
        """
        results = self.model.predict(
            source=image_path,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            save=False,  # We'll save manually with better control
            show=show,
            save_txt=False,
            save_conf=True,
            verbose=False,
        )
        
        if save_path and results:
            # Save annotated image with class labels
            annotated = results[0].plot()
            cv2.imwrite(save_path, annotated)
            
        return results
    
    def predict_video(self, video_path: str, output_path: str = None, show: bool = False):
        """
        Run inference on a video
        
        Args:
            video_path: Path to input video
            output_path: Path to save annotated video (optional)
            show: Whether to display the result
            
        Returns:
            Generator of Results objects from YOLO
        """
        results = self.model.predict(
            source=video_path,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            save=output_path is not None,
            show=show,
            stream=True,
            verbose=False,
        )
        
        return results
    
    def predict_webcam(self, camera_id: int = 0):
        """
        Run inference on webcam stream
        
        Args:
            camera_id: Camera device ID (default: 0)
        """
        results = self.model.predict(
            source=camera_id,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            show=True,
            stream=True,
        )
        
        for r in results:
            pass  # Streaming will show results automatically
    
    def predict_batch(self, input_dir: str, output_dir: str = None):
        """
        Run inference on a directory of images
        
        Args:
            input_dir: Directory containing input images
            output_dir: Directory to save annotated images (optional)
            
        Returns:
            List of Results objects
        """
        input_path = Path(input_dir)
        image_files = list(input_path.glob('*.jpg')) + list(input_path.glob('*.png')) + \
                     list(input_path.glob('*.jpeg')) + list(input_path.glob('*.JPG'))
        
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        all_results = []
        for img_file in image_files:
            save_path = None
            if output_dir:
                save_path = str(Path(output_dir) / img_file.name)
            
            results = self.predict_image(str(img_file), save_path=save_path)
            all_results.append(results)
            print(f"Processed: {img_file.name}")
        
        return all_results
    
    def get_detection_summary(self, results):
        """
        Get summary of detections from results
        
        Args:
            results: Results object from YOLO
            
        Returns:
            Dictionary with detection counts per class
        """
        if not results or len(results) == 0:
            return {}
        
        result = results[0]
        class_counts = {}
        
        if result.boxes:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        return class_counts
    
    def get_detailed_detections(self, results):
        """
        Get detailed information about each detection
        
        Args:
            results: Results object from YOLO
            
        Returns:
            List of dictionaries with detection details
        """
        if not results or len(results) == 0:
            return []
        
        result = results[0]
        detections = []
        
        if result.boxes:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                confidence = float(box.conf[0])
                bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                
                detections.append({
                    'class_id': class_id,
                    'class_name': class_name,
                    'confidence': confidence,
                    'bbox': bbox
                })
        
        return detections
    
    def print_detections(self, results):
        """
        Print detailed detection information
        
        Args:
            results: Results object from YOLO
        """
        detections = self.get_detailed_detections(results)
        
        if not detections:
            print("No detections found.")
            return
        
        print(f"\nFound {len(detections)} detection(s):")
        print("-" * 70)
        for i, det in enumerate(detections, 1):
            print(f"{i}. {det['class_name']}")
            print(f"   Confidence: {det['confidence']:.2%}")
            print(f"   BBox: [{det['bbox'][0]:.1f}, {det['bbox'][1]:.1f}, {det['bbox'][2]:.1f}, {det['bbox'][3]:.1f}]")
        print("-" * 70)
        
        # Print summary
        summary = self.get_detection_summary(results)
        print("\nSummary:")
        for class_name, count in summary.items():
            print(f"  {class_name}: {count}")


def main():
    parser = argparse.ArgumentParser(description='YOLO Safety Detection Inference')
    parser.add_argument('--model', type=str, 
                       default='yolo12_training/yolo_runs/yolo12_run_3/weights/best.pt',
                       help='Path to model weights')
    parser.add_argument('--source', type=str, required=True,
                       help='Path to image, video, directory, or webcam (use "0" for webcam)')
    parser.add_argument('--output', type=str, default='output',
                       help='Output directory for results')
    parser.add_argument('--conf', type=float, default=0.2,
                       help='Confidence threshold')
    parser.add_argument('--iou', type=float, default=0.7,
                       help='IOU threshold for NMS')
    parser.add_argument('--show', action='store_true',
                       help='Display results')
    parser.add_argument('--imgsz', type=int, default=768,
                       help='Inference image size')
    
    args = parser.parse_args()
    
    # Initialize detector
    detector = SafetyDetector(args.model, args.conf, args.iou)
    
    # Determine source type
    source = args.source
    
    if source.isdigit():
        # Webcam
        print(f"Starting webcam inference (camera {source})...")
        detector.predict_webcam(int(source))
    
    elif Path(source).is_file():
        # Single file (image or video)
        ext = Path(source).suffix.lower()
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            # Image
            print(f"Running inference on image: {source}")
            save_path = str(output_path / f"result_{Path(source).name}")
            results = detector.predict_image(source, save_path=save_path, show=args.show)
            
            # Print detailed detections with class names
            detector.print_detections(results)
            print(f"\n✓ Result saved to: {save_path}")
        
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            # Video
            print(f"Running inference on video: {source}")
            results_gen = detector.predict_video(source, show=args.show)
            
            for i, r in enumerate(results_gen):
                if i % 30 == 0:  # Print every 30 frames
                    summary = detector.get_detection_summary([r])
                    if summary:
                        print(f"Frame {i}: {summary}")
    
    elif Path(source).is_dir():
        # Directory of images
        print(f"Running batch inference on directory: {source}")
        output_path = Path(args.output)
        results = detector.predict_batch(source, str(output_path))
        print(f"\nProcessed {len(results)} images")
        print(f"Results saved to: {output_path}")
    
    else:
        print(f"Error: Source '{source}' not found or invalid")


if __name__ == '__main__':
    main()
