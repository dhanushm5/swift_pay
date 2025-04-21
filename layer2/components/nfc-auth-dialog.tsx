"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "next-auth/react";
import { Loader2, CreditCard, X } from "lucide-react";

interface NFCAuthDialogProps {
  onSuccess?: () => void;
  mode: "register" | "verify" | "payment";
  buttonText?: string;
  standalone?: boolean;
}

export function NFCAuthDialog({ onSuccess, mode, buttonText, standalone = true }: NFCAuthDialogProps) {
  const [isModalOpen, setModalOpen] = useState(false);
  const [isLoading, setLoading] = useState(false);
  const [isScanning, setScanning] = useState(false);
  const { data: session } = useSession();
  const { toast } = useToast();

  // For non-standalone mode, auto-open on mount
  useEffect(() => {
    if (!standalone) {
      openModal();
    }
  }, [standalone]);

  const openModal = () => {
    setModalOpen(true);
    document.body.style.overflow = "hidden"; // Prevent scrolling
  };

  const closeModal = () => {
    if (isLoading) return;
    setModalOpen(false);
    setScanning(false);
    document.body.style.overflow = ""; // Restore scrolling
  };

  const startScanning = async () => {
    if (!session?.user?.name) {
      toast({
        title: "Error",
        description: "User not logged in",
        variant: "destructive",
      });
      return;
    }

    setScanning(true);
    setLoading(true);

    try {
      // Simulate NFC card scan (replace with actual NFC reading logic)
      const cardId = await simulateNFCScan();
      
      if (!cardId) {
        throw new Error("No NFC card detected");
      }

      const apiUrl = process.env.NEXT_PUBLIC_NFC_API_URL;
      if (!apiUrl) {
        throw new Error("NFC API URL is not defined");
      }

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

      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: session.user.name,
          card_id: cardId,
        }),
      });

      const data = await response.json();

      if (data.success) {
        if ((mode === "verify" && !data.verified) || (mode === "payment" && !data.authorized)) {
          toast({
            title: "Authentication Failed",
            description: "NFC card verification failed. Please try again.",
            variant: "destructive",
          });
        } else {
          toast({
            title: "Success",
            description: mode === "register" 
              ? "NFC card registered successfully" 
              : (mode === "verify" ? "NFC card verified successfully" : "Payment authorized successfully"),
          });
          closeModal();
          if (onSuccess) onSuccess();
        }
      } else {
        throw new Error(data.message || "Operation failed");
      }
    } catch (error) {
      console.error("NFC error:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Operation failed",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
      setScanning(false);
    }
  };

  // Simulate NFC card scanning (replace with actual NFC implementation)
  const simulateNFCScan = async (): Promise<string> => {
    return new Promise((resolve) => {
      setTimeout(() => {
        // Generate a random card ID for simulation
        const cardId = Math.random().toString(36).substring(2, 15);
        resolve(cardId);
      }, 2000);
    });
  };

  const renderModalContent = () => {
    if (!isModalOpen) return null;

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4">
          {/* Modal Header */}
          <div className="flex justify-between items-center p-4 border-b">
            <h2 className="text-xl font-semibold">
              {mode === "register" 
                ? "Register Your NFC Card" 
                : mode === "verify" 
                ? "Verify Your NFC Card"
                : "Authorize Payment with NFC Card"}
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
              <div className="relative w-full aspect-video bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden flex items-center justify-center">
                {isScanning ? (
                  <div className="flex flex-col items-center space-y-4">
                    <CreditCard className="h-16 w-16 animate-pulse text-blue-500" />
                    <p className="text-lg font-medium">Scanning for NFC card...</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-4">
                    <CreditCard className="h-16 w-16 text-gray-400" />
                    <p className="text-lg font-medium">Ready to scan NFC card</p>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Modal Footer */}
          <div className="p-4 border-t">
            <Button
              onClick={startScanning}
              className="w-full"
              disabled={isLoading || isScanning}
              size="lg"
            >
              {isLoading || isScanning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isScanning ? "Scanning..." : "Processing..."}
                </>
              ) : (
                <>
                  <CreditCard className="mr-2 h-4 w-4" />
                  {mode === "register" ? "Start Registration" : mode === "verify" ? "Start Verification" : "Scan to Pay"}
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      {standalone && (
        <Button
          variant={mode === "payment" ? "default" : "outline"}
          onClick={openModal}
          className={standalone ? "w-full" : ""}
        >
          {buttonText || (mode === "register" ? "Register NFC Card" : mode === "verify" ? "Verify NFC Card" : "Pay with NFC")}
        </Button>
      )}
      
      {renderModalContent()}
    </>
  );
}