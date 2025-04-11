"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "next-auth/react";
import { Loader2, Camera, X } from "lucide-react";

interface FaceAuthDialogProps {
  onSuccess?: () => void;
  mode: "register" | "verify" | "payment";
  buttonText?: string;
  standalone?: boolean;  // Add this prop to control whether to show the button
}

export function FaceAuthDialog({ onSuccess, mode, buttonText, standalone = true }: FaceAuthDialogProps) {
  // Simple state management
  const [isModalOpen, setModalOpen] = useState(false);
  const [isLoading, setLoading] = useState(false);
  const [isCameraReady, setCameraReady] = useState(false);
  const [isDOMReady, setDOMReady] = useState(false);
  
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  
  // Store media stream in a ref to avoid unnecessary re-renders
  const mediaStreamRef = useRef<MediaStream | null>(null);
  
  // Hooks
  const { data: session } = useSession();
  const { toast } = useToast();

  // For non-standalone mode, auto-open on mount
  useEffect(() => {
    if (!standalone) {
      openModal();
    }
  }, [standalone]);

  // Handle clicks outside the modal
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node) && !isLoading) {
        closeModal();
      }
    };
    
    if (isModalOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isModalOpen, isLoading]);

  // Handle escape key
  useEffect(() => {
    const handleEscKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isLoading) {
        closeModal();
      }
    };
    
    if (isModalOpen) {
      document.addEventListener("keydown", handleEscKey);
    }
    
    return () => {
      document.removeEventListener("keydown", handleEscKey);
    };
  }, [isModalOpen, isLoading]);

  // Mark DOM as ready after modal opens with a delay
  useEffect(() => {
    if (isModalOpen) {
      // Short delay to ensure the DOM elements are fully rendered
      const timer = setTimeout(() => {
        setDOMReady(true);
      }, 500);
      return () => {
        clearTimeout(timer);
        setDOMReady(false);
      };
    }
  }, [isModalOpen]);

  // Start camera when modal and DOM are ready
  useEffect(() => {
    if (isModalOpen && isDOMReady) {
      console.log("DOM is ready, starting camera...");
      startCamera();
    }
    
    return () => {
      if (!isModalOpen) {
        stopCamera();
      }
    };
  }, [isModalOpen, isDOMReady]);

  // Start the camera
  const startCamera = async () => {
    try {
      setCameraReady(false);
      console.log("Starting camera...");
      
      // Clean up any existing streams first
      stopCamera();
      
      // Check if video element is available
      if (!videoRef.current) {
        console.error("Video element not found in DOM yet");
        // Retry after a short delay
        setTimeout(startCamera, 200);
        return;
      }
      
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 480 }
        }
      });
      
      mediaStreamRef.current = mediaStream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        console.log("Camera stream attached to video element");
      } else {
        console.error("Video ref is null");
        stopCamera();
      }
    } catch (error) {
      console.error("Camera access error:", error);
      toast({
        title: "Camera Error",
        description: "Could not access camera. Please check permissions.",
        variant: "destructive",
      });
    }
  };

  // Stop the camera
  const stopCamera = () => {
    if (mediaStreamRef.current) {
      console.log("Stopping camera stream");
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
      setCameraReady(false);
      
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    }
  };

  // Handle video ready state
  const handleVideoReady = () => {
    console.log("Video is ready");
    setCameraReady(true);
  };

  // Open modal and start camera
  const openModal = () => {
    console.log("Opening modal");
    setModalOpen(true);
    document.body.style.overflow = "hidden"; // Prevent scrolling
  };

  // Close modal and stop camera
  const closeModal = () => {
    if (isLoading) return;
    
    console.log("Closing modal");
    setModalOpen(false);
    setDOMReady(false);
    document.body.style.overflow = ""; // Restore scrolling
    stopCamera();
  };

  // Capture image from video
  const captureImage = async (): Promise<Blob> => {
    return new Promise((resolve, reject) => {
      if (!videoRef.current || !canvasRef.current) {
        reject(new Error("Video or canvas not initialized"));
        return;
      }

      const video = videoRef.current;
      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");

      if (!context) {
        reject(new Error("Could not get canvas context"));
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error("Could not capture image"));
        }
      }, "image/jpeg");
    });
  };

  // Handle capture button click
  const handleCapture = async () => {
    if (!session?.user?.name) {
      toast({
        title: "Error",
        description: "User not logged in",
        variant: "destructive",
      });
      return;
    }

    if (!isCameraReady || !mediaStreamRef.current) {
      toast({
        title: "Error",
        description: "Camera is not ready yet",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);

    try {
      console.log("Capturing image...");
      const imageBlob = await captureImage();
      
      const formData = new FormData();
      formData.append("file", imageBlob);
      formData.append("username", session.user.name);

      let endpoint = "";
      switch (mode) {
        case "register":
          endpoint = "/register";
          break;
        case "verify":
          endpoint = "/verify";
          break;
        case "payment":
          endpoint = "/authorize-payment";
          break;
      }

      const apiUrl = process.env.NEXT_PUBLIC_FACE_API_URL;
      if (!apiUrl) {
        throw new Error("Face API URL is not defined");
      }
      
      console.log(`Sending request to ${apiUrl}${endpoint} for user ${session.user.name}`);
      
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      console.log("Server response:", data);

      if (data.success) {
        if ((mode === "verify" && !data.verified) || (mode === "payment" && !data.authorized)) {
          toast({
            title: "Authentication Failed",
            description: "Face verification failed. Please try again.",
            variant: "destructive",
          });
          setLoading(false);
        } else {
          toast({
            title: "Success",
            description: mode === "register" 
              ? "Face registered successfully" 
              : (mode === "verify" ? "Face verified successfully" : "Payment authorized successfully"),
          });
          
          closeModal();
          if (onSuccess) onSuccess();
        }
      } else {
        throw new Error(data.message || "Operation failed");
      }
    } catch (error) {
      console.error("Face capture error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Operation failed",
        variant: "destructive",
      });
      setLoading(false);
    }
  };

  // Only render the modal content when isModalOpen is true
  const renderModalContent = () => {
    if (!isModalOpen) return null;
    
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div 
          ref={modalRef}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4"
        >
          {/* Modal Header */}
          <div className="flex justify-between items-center p-4 border-b">
            <h2 className="text-xl font-semibold">
              {mode === "register" 
                ? "Register Your Face" 
                : mode === "verify" 
                ? "Verify Your Face"
                : "Authorize Payment with Face"}
            </h2>
            {!isLoading && (
              <button 
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                onClick={closeModal}
              >
                <X className="h-5 w-5" />
              </button>
            )}
          </div>
          
          {/* Modal Content */}
          <div className="p-4">
            <div className="flex flex-col items-center space-y-4">
              <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden">
                {!isCameraReady && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-10">
                    <Loader2 className="h-8 w-8 animate-spin text-white" />
                    <span className="text-white ml-2">Starting camera...</span>
                  </div>
                )}
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  onCanPlay={handleVideoReady}
                  className="w-full h-full object-cover"
                />
                <canvas ref={canvasRef} className="hidden" />
              </div>
            </div>
          </div>
          
          {/* Modal Footer */}
          <div className="p-4 border-t">
            <Button
              onClick={handleCapture}
              className="w-full"
              disabled={isLoading || !isCameraReady}
              size="lg"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Camera className="mr-2 h-4 w-4" />
                  {mode === "register" ? "Register" : mode === "verify" ? "Verify" : "Authorize"}
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  };

  // Render the component
  return (
    <>
      {/* Only show the button in standalone mode */}
      {standalone && (
        <Button
          variant={mode === "payment" ? "default" : "outline"}
          onClick={openModal}
          className={standalone ? "w-full" : ""}
        >
          {buttonText || (mode === "register" ? "Register Face" : mode === "verify" ? "Verify Face" : "Pay with Face")}
        </Button>
      )}
      
      {/* Modal content */}
      {renderModalContent()}
    </>
  );
}