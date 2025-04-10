// SPDX-License-Identifier: SEE LICENSE IN LICENSE
pragma solidity ^0.8.28;

import "./lib.sol";

// define the transaction block

contract TransactionBlock {
    uint256 public sender_uuid;
    uint256 public receiver_uuid;
    uint256 public amount;
    uint256 public timestamp;
    uint256 public transactionid;
    bytes32 public previousHash;

    constructor(
        uint256 _sender_uuid,
        uint256 _receiver_uuid,
        uint256 _amount,
        uint256 _transactionid,
        bytes32 _previousHash
    ) {
        sender_uuid = _sender_uuid;
        receiver_uuid = _receiver_uuid;
        amount = _amount;
        timestamp = block.timestamp;
        transactionid = _transactionid;
        previousHash = _previousHash;
    }

    function getBlockHash() public view returns (bytes32) {
        // use keccak256 to hash the block
        return keccak256(abi.encodePacked(
            sender_uuid,
            receiver_uuid,
            amount,
            timestamp,
            transactionid,
            previousHash
        ));
    }
}

contract TransactionChain {
    using TransactionLibrary for mapping(uint256 => uint256);
    
    // User management
    mapping(uint256 => bool) public userExists;
    mapping(uint256 => uint256) public balances;
    // Add username mappings
    mapping(string => uint256) private usernameToUuid;
    mapping(uint256 => string) private uuidToUsername;
    mapping(string => bool) private usernameExists;
    
    // Transaction management
    mapping(uint256 => bool) public transactionIdExists;
    TransactionBlock[] public transactionBlocks;
    uint256 private nextTxId = 1; // Auto-incrementing transaction ID
    
    // Transaction tracking
    mapping(uint256 => uint256[]) private userTransactions; // Maps uuid to array of transaction indices
    mapping(uint256 => uint256[]) private userReceivedTransactions; // Maps uuid to array of received transaction indices
    mapping(uint256 => uint256[]) private userSentTransactions; // Maps uuid to array of sent transaction indices

    event UserCreated(uint256 indexed uuid, string username, uint256 timestamp);
    event TransactionCreated(uint256 indexed sender, uint256 indexed receiver, uint256 amount, uint256 timestamp, uint256 transactionid);
    event BalanceAdded(uint256 indexed uuid, uint256 amount, uint256 newBalance);
    event BalanceDeducted(uint256 indexed uuid, uint256 amount, uint256 newBalance);

    /**
     * @dev Creates a new user with a generated UUID and given username
     * @param username The username for the new user
     * @return uuid The generated UUID for the user
     */
    function createUserWithName(string memory username) public returns (uint256) {
        require(!usernameExists[username], "Username already exists");
        
        // Generate UUID based on username and timestamp
        uint256 uuid = uint256(keccak256(abi.encodePacked(username, block.timestamp, msg.sender))) % 10000000000;
        
        // Ensure UUID is unique
        while(userExists[uuid]) {
            uuid = uint256(keccak256(abi.encodePacked(uuid, block.timestamp))) % 10000000000;
        }
        
        userExists[uuid] = true;
        usernameExists[username] = true;
        usernameToUuid[username] = uuid;
        uuidToUsername[uuid] = username;
        balances[uuid] = 0;
        
        emit UserCreated(uuid, username, block.timestamp);
        return uuid;
    }

    /**
     * @dev Gets a user's UUID by their username
     * @param username The username to lookup
     * @return The user's UUID
     */
    function getUserIdByName(string memory username) public view returns (uint256) {
        require(usernameExists[username], "Username does not exist");
        return usernameToUuid[username];
    }

    /**
     * @dev Gets a user's username by their UUID
     * @param uuid The UUID to lookup
     * @return The user's username
     */
    function getUserNameById(uint256 uuid) public view returns (string memory) {
        require(userExists[uuid], "User does not exist");
        return uuidToUsername[uuid];
    }
    
    /**
     * @dev Checks if a user exists by their username
     * @param username The username to check
     * @return true if the user exists, false otherwise
     */
    function validateUserByName(string memory username) public view returns (bool) {
        return usernameExists[username];
    }
    
    /**
     * @dev Creates a new user with the given UUID
     * @param uuid The user's UUID
     * @return true if user was created, false if user already exists
     */
    function createUser(uint256 uuid) public returns (bool) {
        if (userExists[uuid]) {
            return false;
        }
        
        userExists[uuid] = true;
        balances[uuid] = 0;
        
        emit UserCreated(uuid, "", block.timestamp);
        return true;
    }
    
    /**
     * @dev Checks if a user exists
     * @param uuid The user's UUID to check
     * @return true if the user exists, false otherwise
     */
    function validateUser(uint256 uuid) public view returns (bool) {
        return TransactionLibrary.validateUser(userExists, uuid);
    }
    
    /**
     * @dev Checks if a transaction ID already exists
     * @param txid The transaction ID to validate
     * @return true if the transaction ID is unique, false if it already exists
     */
    function validateId(uint256 txid) public view returns (bool) {
        return TransactionLibrary.validateTransactionId(transactionIdExists, txid);
    }
    
    /**
     * @dev Validates if sender has sufficient balance for a transaction
     * @param sender The sender's UUID
     * @param amount The transaction amount
     * @return true if the sender has sufficient balance, false otherwise
     */
    function transactionValidate(uint256 sender, uint256 amount) public view returns (bool) {
        return TransactionLibrary.validateTransaction(balances, sender, amount);
    }
    
    /**
     * @dev Creates a transaction between users with auto-generated transaction ID
     * @param sender The sender's UUID
     * @param receiver The receiver's UUID
     * @param amount The transaction amount
     * @return txid The generated transaction ID
     */
    function createTransactionAuto(
        uint256 sender, 
        uint256 receiver,
        uint256 amount
    ) public returns (uint256) {
        // Validate all inputs
        require(validateUser(sender), "Sender does not exist");
        require(validateUser(receiver), "Receiver does not exist");
        require(transactionValidate(sender, amount), "Insufficient balance");

        // Generate unique transaction ID
        uint256 txid = nextTxId;
        nextTxId += 1;

        // Transfer balance
        bool success = TransactionLibrary.transferBalance(balances, sender, receiver, amount);
        require(success, "Balance transfer failed");

        // Mark transaction ID as used
        transactionIdExists[txid] = true;

        // Calculate previous block hash
        bytes32 previousHash = transactionBlocks.length > 0 ? 
            transactionBlocks[transactionBlocks.length - 1].getBlockHash() : 
            bytes32(0);

        // Create new transaction block
        TransactionBlock newBlock = new TransactionBlock(
            sender, 
            receiver, 
            amount, 
            txid, 
            previousHash
        );

        // Add to blockchain
        uint256 newBlockIndex = transactionBlocks.length;
        transactionBlocks.push(newBlock);

        // Update the mappings for transaction tracking
        userTransactions[sender].push(newBlockIndex);
        userTransactions[receiver].push(newBlockIndex);
        userSentTransactions[sender].push(newBlockIndex);
        userReceivedTransactions[receiver].push(newBlockIndex);

        emit TransactionCreated(sender, receiver, amount, block.timestamp, txid);

        return txid;
    }
    
    /**
     * @dev Creates a transaction between users
     * @param sender The sender's UUID
     * @param receiver The receiver's UUID
     * @param amount The transaction amount
     * @param txid The transaction ID
     * @return true if successful, false otherwise
     */
    function createTransaction(
        uint256 sender, 
        uint256 receiver,
        uint256 amount,
        uint256 txid
    ) public returns (bool) {
        // Validate all inputs
        require(validateUser(sender), "Sender does not exist");
        require(validateUser(receiver), "Receiver does not exist");
        require(validateId(txid), "Transaction ID already exists");
        require(transactionValidate(sender, amount), "Insufficient balance");

        // Transfer balance
        bool success = TransactionLibrary.transferBalance(balances, sender, receiver, amount);
        require(success, "Balance transfer failed");

        // Mark transaction ID as used
        transactionIdExists[txid] = true;

        // Calculate previous block hash
        bytes32 previousHash = transactionBlocks.length > 0 ? 
            transactionBlocks[transactionBlocks.length - 1].getBlockHash() : 
            bytes32(0);

        // Create new transaction block
        TransactionBlock newBlock = new TransactionBlock(
            sender, 
            receiver, 
            amount, 
            txid, 
            previousHash
        );

        // Add to blockchain
        uint256 newBlockIndex = transactionBlocks.length;
        transactionBlocks.push(newBlock);

        // Update the mappings for transaction tracking
        userTransactions[sender].push(newBlockIndex);
        userTransactions[receiver].push(newBlockIndex);
        userSentTransactions[sender].push(newBlockIndex);
        userReceivedTransactions[receiver].push(newBlockIndex);

        emit TransactionCreated(sender, receiver, amount, block.timestamp, txid);

        return true;
    }
    
    /**
     * @dev Gets detailed information about a transaction by its ID
     * @param txid The transaction ID to lookup
     * @return found Whether the transaction was found
     * @return sender The sender's UUID
     * @return receiver The receiver's UUID
     * @return amount The transaction amount
     * @return timestamp The transaction timestamp
     */
    function getTransaction(uint256 txid) public view returns (
        bool found,
        uint256 sender,
        uint256 receiver,
        uint256 amount,
        uint256 timestamp
    ) {
        // If transaction ID doesn't exist, return not found
        if (!transactionIdExists[txid]) {
            return (false, 0, 0, 0, 0);
        }
        
        // Find the transaction by ID
        for (uint256 i = 0; i < transactionBlocks.length; i++) {
            TransactionBlock txBlock = transactionBlocks[i];
            if (txBlock.transactionid() == txid) {
                return (
                    true,
                    txBlock.sender_uuid(),
                    txBlock.receiver_uuid(),
                    txBlock.amount(),
                    txBlock.timestamp()
                );
            }
        }
        
        // Transaction ID exists but not found (should never happen)
        return (false, 0, 0, 0, 0);
    }

    /**
     * @dev Gets detailed information about a transaction by its index in the blocks array
     * @param index The index of the transaction in the blocks array
     * @return found Whether the transaction was found
     * @return sender The sender's UUID
     * @return receiver The receiver's UUID
     * @return amount The transaction amount
     * @return timestamp The transaction timestamp
     * @return txId The transaction ID
     * @return prevHash The previous block hash
     */
    function getTransactionDetailsByIndex(uint256 index) public view returns (
        bool found,
        uint256 sender,
        uint256 receiver,
        uint256 amount,
        uint256 timestamp,
        uint256 txId,
        bytes32 prevHash
    ) {
        if (index >= transactionBlocks.length) {
            return (false, 0, 0, 0, 0, 0, bytes32(0));
        }
        
        TransactionBlock txBlock = transactionBlocks[index];
        return (
            true,
            txBlock.sender_uuid(),
            txBlock.receiver_uuid(),
            txBlock.amount(),
            txBlock.timestamp(),
            txBlock.transactionid(),
            txBlock.previousHash()
        );
    }
    
    /**
     * @dev Adds balance to a user's account
     * @param uuid The user's UUID
     * @param amount The amount to add
     * @return success true if successful, false if user doesn't exist
     */
    function userAdd(uint256 uuid, uint256 amount) public returns (bool) {
        if (!validateUser(uuid)) {
            return false;
        }
        
        TransactionLibrary.addBalance(balances, uuid, amount);
        emit BalanceAdded(uuid, amount, balances[uuid]);
        return true;
    }
    
    /**
     * @dev Adds balance to a user's account via ETH transfer
     * @param uuid The user's UUID
     */
    function deposit(uint256 uuid) public payable {
        require(validateUser(uuid), "User does not exist");
        balances[uuid] += msg.value;
        emit BalanceAdded(uuid, msg.value, balances[uuid]);
    }
    
    /**
     * @dev Deducts balance from a user's account
     * @param uuid The user's UUID
     * @param amount The amount to deduct
     * @return true if successful, false otherwise
     */
    function userDeduct(uint256 uuid, uint256 amount) public returns (bool) {
        if (!validateUser(uuid)) {
            return false;
        }
        
        bool success = TransactionLibrary.deductBalance(balances, uuid, amount);
        if (success) {
            emit BalanceDeducted(uuid, amount, balances[uuid]);
        }
        return success;
    }
    
    /**
     * @dev Returns the number of transactions in the blockchain
     * @return The transaction count
     */
    function getTransactionCount() public view returns (uint256) {
        return transactionBlocks.length;
    }
    
    /**
     * @dev Returns an array of transaction indices involving the specified user
     * @param uuid The user's UUID
     * @return An array of transaction indices
     */
    function userTransactionIndices(uint256 uuid) public view returns (uint256[] memory) {
        return userTransactions[uuid];
    }

    /**
     * @dev Returns an array of transaction indices where the user received money
     * @param uuid The user's UUID
     * @return An array of transaction indices
     */
    function userReceivedIndices(uint256 uuid) public view returns (uint256[] memory) {
        return userReceivedTransactions[uuid];
    }

    /**
     * @dev Returns an array of transaction indices where the user sent money
     * @param uuid The user's UUID
     * @return An array of transaction indices
     */
    function userSentIndices(uint256 uuid) public view returns (uint256[] memory) {
        return userSentTransactions[uuid];
    }

    /**
     * @dev Returns all transactions involving the user
     * @param uuid The user's UUID
     * @return txIds Array of transaction IDs
     * @return senders Array of sender UUIDs
     * @return receivers Array of receiver UUIDs
     * @return amounts Array of transaction amounts
     */
    function getUserTransactions(uint256 uuid) public view returns (
        uint256[] memory txIds,
        uint256[] memory senders,
        uint256[] memory receivers,
        uint256[] memory amounts
    ) {
        uint256[] memory indices = userTransactions[uuid];
        txIds = new uint256[](indices.length);
        senders = new uint256[](indices.length);
        receivers = new uint256[](indices.length);
        amounts = new uint256[](indices.length);

        for (uint256 i = 0; i < indices.length; i++) {
            TransactionBlock txBlock = transactionBlocks[indices[i]];
            txIds[i] = txBlock.transactionid();
            senders[i] = txBlock.sender_uuid();
            receivers[i] = txBlock.receiver_uuid();
            amounts[i] = txBlock.amount();
        }

        return (txIds, senders, receivers, amounts);
    }

    /**
     * @dev Returns all transactions where the user received money
     * @param uuid The user's UUID
     * @return txIds Array of transaction IDs
     * @return senders Array of sender UUIDs
     * @return amounts Array of transaction amounts
     */
    function userReceived(uint256 uuid) public view returns (
        uint256[] memory txIds,
        uint256[] memory senders,
        uint256[] memory amounts
    ) {
        uint256[] memory indices = userReceivedTransactions[uuid];
        txIds = new uint256[](indices.length);
        senders = new uint256[](indices.length);
        amounts = new uint256[](indices.length);

        for (uint256 i = 0; i < indices.length; i++) {
            TransactionBlock txBlock = transactionBlocks[indices[i]];
            txIds[i] = txBlock.transactionid();
            senders[i] = txBlock.sender_uuid();
            amounts[i] = txBlock.amount();
        }

        return (txIds, senders, amounts);
    }

    /**
     * @dev Returns all transactions where the user sent money
     * @param uuid The user's UUID
     * @return txIds Array of transaction IDs
     * @return receivers Array of receiver UUIDs
     * @return amounts Array of transaction amounts
     */
    function userSent(uint256 uuid) public view returns (
        uint256[] memory txIds,
        uint256[] memory receivers,
        uint256[] memory amounts
    ) {
        uint256[] memory indices = userSentTransactions[uuid];
        txIds = new uint256[](indices.length);
        receivers = new uint256[](indices.length);
        amounts = new uint256[](indices.length);

        for (uint256 i = 0; i < indices.length; i++) {
            TransactionBlock txBlock = transactionBlocks[indices[i]];
            txIds[i] = txBlock.transactionid();
            receivers[i] = txBlock.receiver_uuid();
            amounts[i] = txBlock.amount();
        }

        return (txIds, receivers, amounts);
    }

}