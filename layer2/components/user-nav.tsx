"use client";

import { useSession, signOut } from "next-auth/react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { FaceAuthDialog } from "@/components/face-auth-dialog";
import { NFCAuthDialog } from "@/components/nfc-auth-dialog";
import { useState } from "react";

export function UserNav() {
  const { data: session } = useSession();
  const [isDropdownOpen, setDropdownOpen] = useState(false);
  const [showRegisterFaceModal, setShowRegisterFaceModal] = useState(false);
  const [showVerifyFaceModal, setShowVerifyFaceModal] = useState(false);
  const [showRegisterNFCModal, setShowRegisterNFCModal] = useState(false);
  const [showVerifyNFCModal, setShowVerifyNFCModal] = useState(false);

  const handleRegisterFace = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDropdownOpen(false);
    setShowRegisterFaceModal(true);
  };
  
  const handleVerifyFace = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDropdownOpen(false);
    setShowVerifyFaceModal(true);
  };

  const handleRegisterNFC = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDropdownOpen(false);
    setShowRegisterNFCModal(true);
  };
  
  const handleVerifyNFC = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDropdownOpen(false);
    setShowVerifyNFCModal(true);
  };

  return (
    <>
      <DropdownMenu open={isDropdownOpen} onOpenChange={setDropdownOpen}>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="relative h-8 w-8 rounded-full">
            <Avatar className="h-8 w-8">
              <AvatarFallback>
                {session?.user?.name?.[0]?.toUpperCase()}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end" forceMount>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">
                {session?.user?.name}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
            <Button 
              variant="outline" 
              className="w-full" 
              onClick={handleRegisterFace}
            >
              Register Face ID
            </Button>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
            <Button 
              variant="outline" 
              className="w-full" 
              onClick={handleVerifyFace}
            >
              Verify Face ID
            </Button>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
            <Button 
              variant="outline" 
              className="w-full" 
              onClick={handleRegisterNFC}
            >
              Register NFC Card
            </Button>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
            <Button 
              variant="outline" 
              className="w-full" 
              onClick={handleVerifyNFC}
            >
              Verify NFC Card
            </Button>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="cursor-pointer"
            onSelect={() => signOut({ callbackUrl: "/login" })}
          >
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      
      {/* Authentication modals */}
      {showRegisterFaceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-4">
              <FaceAuthDialog 
                mode="register" 
                onSuccess={() => setShowRegisterFaceModal(false)} 
              />
            </div>
            <div className="p-4 border-t">
              <Button 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowRegisterFaceModal(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {showVerifyFaceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-4">
              <FaceAuthDialog 
                mode="verify" 
                onSuccess={() => setShowVerifyFaceModal(false)} 
              />
            </div>
            <div className="p-4 border-t">
              <Button 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowVerifyFaceModal(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {showRegisterNFCModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-4">
              <NFCAuthDialog 
                mode="register" 
                onSuccess={() => setShowRegisterNFCModal(false)} 
              />
            </div>
            <div className="p-4 border-t">
              <Button 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowRegisterNFCModal(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {showVerifyNFCModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-4">
              <NFCAuthDialog 
                mode="verify" 
                onSuccess={() => setShowVerifyNFCModal(false)} 
              />
            </div>
            <div className="p-4 border-t">
              <Button 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowVerifyNFCModal(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}