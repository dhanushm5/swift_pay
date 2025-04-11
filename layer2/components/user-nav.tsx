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
import { useState } from "react";

export function UserNav() {
  const { data: session } = useSession();
  const [isDropdownOpen, setDropdownOpen] = useState(false);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [showVerifyModal, setShowVerifyModal] = useState(false);

  const handleRegister = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent the dropdown from closing
    setDropdownOpen(false); // Close dropdown manually
    setShowRegisterModal(true); // Open registration modal
  };
  
  const handleVerify = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent the dropdown from closing
    setDropdownOpen(false); // Close dropdown manually
    setShowVerifyModal(true); // Open verify modal
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
              onClick={handleRegister}
            >
              Register Face ID
            </Button>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
            <Button 
              variant="outline" 
              className="w-full" 
              onClick={handleVerify}
            >
              Verify Face ID
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
      
      {/* Face authentication modals outside the dropdown */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-4">
              <FaceAuthDialog 
                mode="register" 
                onSuccess={() => setShowRegisterModal(false)} 
              />
            </div>
            <div className="p-4 border-t">
              <Button 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowRegisterModal(false)}
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
      
      {showVerifyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-4">
              <FaceAuthDialog 
                mode="verify" 
                onSuccess={() => setShowVerifyModal(false)} 
              />
            </div>
            <div className="p-4 border-t">
              <Button 
                variant="outline" 
                className="w-full" 
                onClick={() => setShowVerifyModal(false)}
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