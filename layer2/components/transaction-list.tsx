"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/use-toast";
import { Loader2 } from "lucide-react";

interface Transaction {
  id: number;
  sender: {
    username: string;
  };
  receiver: {
    username: string;
  };
  amount: number;
  timestamp: string;
}

export function TransactionList() {
  const { data: session } = useSession();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    const fetchTransactions = async () => {
      if (!session?.user?.name) return;

      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transactions/by-user`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: session.user.name }),
        });

        const data = await res.json();
        setTransactions(data.transactions || []);
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to fetch transactions",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchTransactions();
  }, [session]);

  if (isLoading) {
    return (
      <div className="flex justify-center p-4">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Recent Transactions</h2>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>From</TableHead>
              <TableHead>To</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {transactions.map((tx) => (
              <TableRow key={tx.id}>
                <TableCell>{tx.id}</TableCell>
                <TableCell>{tx.sender.username}</TableCell>
                <TableCell>{tx.receiver.username}</TableCell>
                <TableCell>{tx.amount}</TableCell>
                <TableCell>
                  {tx.timestamp ? new Date(tx.timestamp).toLocaleString() : "N/A"}
                </TableCell>
              </TableRow>
            ))}
            {transactions.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center">
                  No transactions found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}