import { ethers } from "hardhat";
import * as readline from 'readline';

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

async function main() {
    console.log("=== Blockchain Transaction Manager ===");
    
    // Deploy or connect to contract
    const contractAddress = await askQuestion("Enter contract address (leave empty to deploy new): ");
    let transactionChain;

    if (contractAddress === "") {
        console.log("Deploying new contract...");
        const TransactionChain = await ethers.getContractFactory("TransactionChain");
        transactionChain = await TransactionChain.deploy();
        await transactionChain.waitForDeployment();
        const address = await transactionChain.getAddress();
        console.log(`Contract deployed at: ${address}\nYou can use this address next time.`);
    } else {
        const TransactionChain = await ethers.getContractFactory("TransactionChain");
        transactionChain = TransactionChain.attach(contractAddress);
        console.log("Connected to existing contract");
    }

    // Main menu
    while (true) {
        console.log("\n=== Main Menu ===");
        console.log("1. User Management");
        console.log("2. Balance Management");
        console.log("3. Transaction Management");
        console.log("4. View Data");
        console.log("5. Exit");

        const choice = await askQuestion("Enter your choice (1-5): ");

        switch (choice) {
            case '1':
                await userManagement(transactionChain);
                break;
            case '2':
                await balanceManagement(transactionChain);
                break;
            case '3':
                await transactionManagement(transactionChain);
                break;
            case '4':
                await viewData(transactionChain);
                break;
            case '5':
                console.log("Exiting...");
                rl.close();
                return;
            default:
                console.log("Invalid choice. Please try again.");
        }
    }
}

// Helper functions
function askQuestion(question: string): Promise<string> {
    return new Promise((resolve) => {
        rl.question(question, (answer) => {
            resolve(answer.trim());
        });
    });
}

async function userManagement(contract: any) {
    while (true) {
        console.log("\n=== User Management ===");
        console.log("1. Create User");
        console.log("2. Check User Exists");
        console.log("3. Back to Main Menu");

        const choice = await askQuestion("Enter your choice (1-3): ");

        switch (choice) {
            case '1':
                const username = await askQuestion("Enter username: ");
                try {
                    const tx = await contract.createUserWithName(username);
                    await tx.wait();
                    // Get the assigned UUID to show to the user
                    const userId = await contract.getUserIdByName(username);
                    console.log(`User "${username}" created successfully with ID: ${userId}!`);
                } catch (error) {
                    console.log(`Error: ${error.reason || error.message}`);
                }
                break;
            case '2':
                const checkUsername = await askQuestion("Enter username to check: ");
                try {
                    const exists = await contract.validateUserByName(checkUsername);
                    console.log(`User "${checkUsername}" ${exists ? "exists" : "does not exist"}`);
                    if (exists) {
                        const userId = await contract.getUserIdByName(checkUsername);
                        console.log(`User ID: ${userId}`);
                    }
                } catch (error) {
                    console.log(`Error checking user: ${error.message}`);
                }
                break;
            case '3':
                return;
            default:
                console.log("Invalid choice. Please try again.");
        }
    }
}

async function balanceManagement(contract: any) {
    while (true) {
        console.log("\n=== Balance Management ===");
        console.log("1. Add Balance");
        console.log("2. Deposit ETH");
        console.log("3. Check Balance");
        console.log("4. Back to Main Menu");

        const choice = await askQuestion("Enter your choice (1-4): ");

        switch (choice) {
            case '1':
                const addUsername = await askQuestion("Enter username: ");
                const addAmount = parseInt(await askQuestion("Enter amount to add: "));
                try {
                    // First get the user ID from username
                    const userId = await contract.getUserIdByName(addUsername);
                    const tx = await contract.userAdd(userId, addAmount);
                    await tx.wait();
                    const newBalance = await contract.balances(userId);
                    console.log(`Added ${addAmount} to ${addUsername}. New balance: ${newBalance}`);
                } catch (error) {
                    console.log(`Error: ${error.reason || error.message}`);
                }
                break;
            case '2':
                const depositUsername = await askQuestion("Enter username: ");
                const depositAmount = await askQuestion("Enter ETH amount to deposit: ");
                try {
                    const userId = await contract.getUserIdByName(depositUsername);
                    const tx = await contract.deposit(userId, { 
                        value: ethers.parseEther(depositAmount) 
                    });
                    await tx.wait();
                    const newBalance = await contract.balances(userId);
                    console.log(`Deposited ${depositAmount} ETH to ${depositUsername}. New balance: ${newBalance}`);
                } catch (error) {
                    console.log(`Error: ${error.reason || error.message}`);
                }
                break;
            case '3':
                const balanceUsername = await askQuestion("Enter username: ");
                try {
                    const userId = await contract.getUserIdByName(balanceUsername);
                    const balance = await contract.balances(userId);
                    console.log(`Balance for user ${balanceUsername}: ${balance}`);
                } catch (error) {
                    console.log(`Error: ${error.message}`);
                }
                break;
            case '4':
                return;
            default:
                console.log("Invalid choice. Please try again.");
        }
    }
}

async function transactionManagement(contract: any) {
    while (true) {
        console.log("\n=== Transaction Management ===");
        console.log("1. Create Transaction");
        console.log("2. Back to Main Menu");

        const choice = await askQuestion("Enter your choice (1-2): ");

        switch (choice) {
            case '1':
                const senderUsername = await askQuestion("Enter sender username: ");
                const receiverUsername = await askQuestion("Enter receiver username: ");
                const amount = parseInt(await askQuestion("Enter amount: "));
                
                try {
                    const senderId = await contract.getUserIdByName(senderUsername);
                    const receiverId = await contract.getUserIdByName(receiverUsername);
                    
                    // Let contract generate transaction ID
                    const tx = await contract.createTransactionAuto(
                        senderId, 
                        receiverId, 
                        amount
                    );
                    const receipt = await tx.wait();
                    
                    // Extract the transaction ID from event logs
                    let txId = "N/A";
                    try {
                        // Parse the transaction receipt events
                        const event = receipt.logs.find(log => {
                            // Try to detect TransactionCreated event by analyzing the log
                            try {
                                const parsedLog = contract.interface.parseLog(log);
                                return parsedLog?.name === "TransactionCreated";
                            } catch (e) {
                                return false;
                            }
                        });
                        
                        if (event) {
                            const parsedEvent = contract.interface.parseLog(event);
                            // The 'transactionid' should be the 5th parameter in your event
                            // (indexed sender, indexed receiver, amount, timestamp, transactionid)
                            txId = parsedEvent.args[4].toString();
                        } else {
                            // Alternative: Get the last transaction ID directly
                            const lastTxCount = await contract.getTransactionCount();
                            if (lastTxCount > 0) {
                                // If this doesn't return the expected ID, you may need contract-specific logic
                                txId = (lastTxCount).toString();
                            }
                        }
                    } catch (e) {
                        console.log(`Note: Could not extract transaction ID from events: ${e.message}`);
                    }
                    
                    console.log(`Transaction created successfully! Transaction ID: ${txId}`);
                } catch (error) {
                    console.log(`Transaction failed: ${error.reason || error.message}`);
                }
                break;
            case '2':
                return;
            default:
                console.log("Invalid choice. Please try again.");
        }
    }
}

async function viewData(contract: any) {
    while (true) {
        console.log("\n=== View Data ===");
        console.log("1. View All Transactions");
        console.log("2. View User Transactions");
        console.log("3. View User Received");
        console.log("4. View User Sent");
        console.log("5. View Transaction by ID");
        console.log("6. Back to Main Menu");

        const choice = await askQuestion("Enter your choice (1-6): ");

        switch (choice) {
            case '1':
                await showAllTransactions(contract);
                break;
            case '2':
                await showUserTransactions(contract);
                break;
            case '3':
                await showReceivedTransactions(contract);
                break;
            case '4':
                await showSentTransactions(contract);
                break;
            case '5':
                await showTransactionById(contract);
                break;
            case '6':
                return;
            default:
                console.log("Invalid choice. Please try again.");
        }
    }
}

async function showAllTransactions(contract: any) {
    try {
        const txCount = await contract.getTransactionCount();
        console.log(`\nTotal transactions: ${txCount}`);

        if (txCount === 0) {
            console.log("No transactions found.");
            return;
        }

        for (let i = 0; i < txCount; i++) {
            // Instead of trying to access the transaction block directly, use the getTransactionDetails method
            try {
                // Get detailed transaction information using transaction index
                const [found, sender, receiver, amount, timestamp, txId, prevHash] = await contract.getTransactionDetailsByIndex(i);
                
                if (!found) {
                    console.log(`\nTransaction #${i + 1}: Not found or invalid`);
                    continue;
                }
                
                // Get usernames for the sender and receiver UUIDs
                let senderName = sender.toString();
                let receiverName = receiver.toString();
                
                try {
                    senderName = await contract.getUserNameById(sender);
                    receiverName = await contract.getUserNameById(receiver);
                } catch (e) {
                    // If username lookup fails, we'll use the UUIDs
                }
                
                console.log(`\nTransaction Block #${i + 1}:`);
                console.log(`- Sender: ${senderName} (ID: ${sender})`);
                console.log(`- Receiver: ${receiverName} (ID: ${receiver})`);
                console.log(`- Amount: ${amount}`);
                console.log(`- Timestamp: ${new Date(Number(timestamp) * 1000)}`);
                console.log(`- TX ID: ${txId}`);
                console.log(`- Previous Hash: ${prevHash}`);
            } catch (error) {
                console.log(`Error retrieving transaction #${i + 1}: ${error.message}`);
            }
        }
    } catch (error) {
        console.log(`Error fetching transactions: ${error.message}`);
    }
}

async function showUserTransactions(contract: any) {
    const username = await askQuestion("Enter username: ");
    
    try {
        const userId = await contract.getUserIdByName(username);    
        const userExists = await contract.validateUser(userId);
        if (!userExists) {
            console.log(`User "${username}" does not exist.`);
            return;
        }

        const [txIds, senders, receivers, amounts] = await contract.getUserTransactions(userId);
        
        console.log(`\nTransactions for User "${username}" (ID: ${userId}):`);
        console.log("-------------------------------");
        
        if (txIds.length === 0) {
            console.log("No transactions found for this user.");
            return;
        }

        for (let i = 0; i < txIds.length; i++) {
            // Try to get usernames from IDs for better display
            let senderName = senders[i].toString();
            let receiverName = receivers[i].toString();
            try {
                senderName = await contract.getUserNameById(senders[i]);
                receiverName = await contract.getUserNameById(receivers[i]);
            } catch (e) {
                // Fallback to IDs if name lookup fails
            }
            
            console.log(`\nTransaction #${i + 1}:`);
            console.log(`- ID: ${txIds[i]}`);
            console.log(`- Sender: ${senderName} (ID: ${senders[i]})`);
            console.log(`- Receiver: ${receiverName} (ID: ${receivers[i]})`);
            console.log(`- Amount: ${amounts[i]}`);
        }
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

async function showReceivedTransactions(contract: any) {
    const username = await askQuestion("Enter username: ");
    
    try {
        const userId = await contract.getUserIdByName(username);
        const userExists = await contract.validateUser(userId);
        if (!userExists) {
            console.log(`User "${username}" does not exist.`);
            return;
        }

        const [txIds, senders, amounts] = await contract.userReceived(userId);
        
        console.log(`\nReceived Transactions for User "${username}" (ID: ${userId}):`);
        console.log("--------------------------------------");
        
        if (txIds.length === 0) {
            console.log("No received transactions found.");
            return;
        }

        for (let i = 0; i < txIds.length; i++) {
            // Try to get sender username for better display
            let senderName = senders[i].toString();
            try {
                senderName = await contract.getUserNameById(senders[i]);
            } catch (e) {
                // Fallback to ID if name lookup fails
            }
            
            console.log(`\nTransaction #${i + 1}:`);
            console.log(`- ID: ${txIds[i]}`);
            console.log(`- From: ${senderName} (ID: ${senders[i]})`);
            console.log(`- Amount: ${amounts[i]}`);
        }
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

async function showSentTransactions(contract: any) {
    const username = await askQuestion("Enter username: ");
    
    try {
        const userId = await contract.getUserIdByName(username);
        const userExists = await contract.validateUser(userId);
        if (!userExists) {
            console.log(`User "${username}" does not exist.`);
            return;
        }

        const [txIds, receivers, amounts] = await contract.userSent(userId);
        
        console.log(`\nSent Transactions for User "${username}" (ID: ${userId}):`);
        console.log("----------------------------------");
        
        if (txIds.length === 0) {
            console.log("No sent transactions found.");
            return;
        }

        for (let i = 0; i < txIds.length; i++) {
            // Try to get receiver username for better display
            let receiverName = receivers[i].toString();
            try {
                receiverName = await contract.getUserNameById(receivers[i]);
            } catch (e) {
                // Fallback to ID if name lookup fails
            }
            
            console.log(`\nTransaction #${i + 1}:`);
            console.log(`- ID: ${txIds[i]}`);
            console.log(`- To: ${receiverName} (ID: ${receivers[i]})`);
            console.log(`- Amount: ${amounts[i]}`);
        }
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

async function showTransactionById(contract: any) {
    const txId = await askQuestion("Enter transaction ID: ");
    
    try {
        const [found, sender, receiver, amount, timestamp] = await contract.getTransaction(txId);
        
        if (!found) {
            console.log(`Transaction ID ${txId} not found.`);
            return;
        }
        
        // Get usernames for the sender and receiver UUIDs
        let senderName = sender.toString();
        let receiverName = receiver.toString();
        
        try {
            senderName = await contract.getUserNameById(sender);
            receiverName = await contract.getUserNameById(receiver);
        } catch (e) {
            // If username lookup fails, we'll use the UUIDs
        }
        
        console.log(`\nTransaction Details for ID ${txId}:`);
        console.log(`- Sender: ${senderName} (ID: ${sender})`);
        console.log(`- Receiver: ${receiverName} (ID: ${receiver})`);
        console.log(`- Amount: ${amount}`);
        console.log(`- Timestamp: ${new Date(Number(timestamp) * 1000)}`);
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
    rl.close();
});