"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { useSession } from "next-auth/react";
import { FaceAuthDialog } from "@/components/face-auth-dialog";
import { NFCAuthDialog } from "@/components/nfc-auth-dialog";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

interface SendMoneyDialogProps {
  onSuccess?: () => void;
}

export function SendMoneyDialog({ onSuccess }: SendMoneyDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [receiver, setReceiver] = useState("");
  const [amount, setAmount] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showFaceAuth, setShowFaceAuth] = useState(false);
  const [showNFCAuth, setShowNFCAuth] = useState(false);
  const [authMethod, setAuthMethod] = useState<"face" | "nfc">("face");
  const { data: session } = useSession();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (authMethod === "face") {
      setShowFaceAuth(true);
    } else {
      setShowNFCAuth(true);
    }
  };

  const handlePayment = async () => {
    setIsLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transactions/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sender_username: session?.user?.name,
          receiver_username: receiver,
          amount: parseInt(amount),
        }),
      });

      const data = await res.json();

      if (data.success) {
        toast({
          title: "Success",
          description: "Payment sent successfully",
        });
        setIsOpen(false);
        onSuccess?.();
      } else {
        throw new Error(data.error || "Failed to send payment");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to send payment",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
      setShowFaceAuth(false);
      setShowNFCAuth(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button>Send Money</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Send Money</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="receiver">Receiver Username</Label>
            <Input
              id="receiver"
              value={receiver}
              onChange={(e) => setReceiver(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="amount">Amount</Label>
            <Input
              id="amount"
              type="number"
              min="1"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label>Authentication Method</Label>
            <RadioGroup
              value={authMethod}
              onValueChange={(value) => setAuthMethod(value as "face" | "nfc")}
              className="flex space-x-4"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="face" id="face" />
                <Label htmlFor="face">Face ID</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="nfc" id="nfc" />
                <Label htmlFor="nfc">NFC Card</Label>
              </div>
            </RadioGroup>
          </div>
          {showFaceAuth ? (
            <FaceAuthDialog
              mode="payment"
              onSuccess={handlePayment}
              buttonText={isLoading ? "Processing..." : "Confirm with Face"}
              standalone={false}
            />
          ) : showNFCAuth ? (
            <NFCAuthDialog
              mode="payment"
              onSuccess={handlePayment}
              buttonText={isLoading ? "Processing..." : "Confirm with NFC"}
              standalone={false}
            />
          ) : (
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Processing..." : "Continue"}
            </Button>
          )}
        </form>
      </DialogContent>
    </Dialog>
  );
}