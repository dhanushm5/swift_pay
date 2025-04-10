# Swift Pay - Blockchain Payment System

Swift Pay is a modern blockchain-based payment system that allows for secure, fast, and transparent transactions between users. Built with a Next.js frontend and blockchain technology backend, Swift Pay combines the best of web development and decentralized finance.

## Project Structure

The project consists of two main layers:

- **Layer 2 (Frontend)**: A Next.js application with React components for user interaction
- **Layer 3 (Backend)**: Blockchain implementation with Solidity smart contracts and FastAPI services

### Smart Contract Structure

The blockchain system consists of two main contracts:

1. **TransactionBlock**: Represents individual transaction blocks in the chain
2. **TransactionChain**: Main contract for managing users, balances, and transactions

## Features

- User authentication and management
- Balance management (add, deposit, check)
- Send and receive payments
- Transaction history tracking (by user, by transaction ID)
- Blockchain-based security with Ethereum smart contracts
- Responsive UI with shadcn components
- RESTful API for interacting with the blockchain

## Tech Stack

### Frontend (Layer 2)
- Next.js 15.x
- React 18.x
- TypeScript
- Tailwind CSS
- shadcn/ui components
- NextAuth.js for authentication

### Backend (Layer 3)
- Python 3.8+ with FastAPI framework
- Solidity for smart contracts
- Hardhat for Ethereum development
- Ethers.js for contract interaction

## Getting Started

### Prerequisites

- Node.js 18.x or higher
- Python 3.8+ or higher
- Git
- Hardhat development environment

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/swift_pay.git
   cd swift_pay
   ```

2. Install frontend dependencies:
   ```bash
   cd layer2
   npm install
   ```

3. Install backend dependencies:
   ```bash
   cd ../layer3
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - For frontend, create a `.env.local` file in the layer2 directory:
     ```
     NEXT_PUBLIC_API_URL=http://localhost:8000
     NEXTAUTH_SECRET=your_nextauth_secret_here_replace_with_strong_random_value
     NEXTAUTH_URL=http://localhost:3000
     ```
   - For backend, create a `.env` file in the layer3 directory:
     ```
     CONTRACT_ADDRESS=your_deployed_contract_address_will_go_here
     HARDHAT_URL=http://localhost:8545
     ```

   > ⚠️ **Security Note**: Never commit these `.env` files to GitHub. They are automatically excluded by the `.gitignore` file.

5. Start the Hardhat blockchain node:
   ```bash
   cd ../layer3
   npx hardhat node
   ```

6. Deploy the smart contract (in a new terminal):
   ```bash
   cd layer3
   npx hardhat run scripts/deploy.ts --network localhost
   ```
   
   Note: You can also deploy the contract using the API after starting the server:
   ```bash
   curl -X POST http://localhost:8000/api/contract/deploy
   ```

7. Start the FastAPI backend server:
   ```bash
   cd layer3
   python app.py
   ```
   The API will be available at http://localhost:8000

8. Start the frontend development server:
   ```bash
   cd ../layer2
   npm run dev
   ```
   The frontend will be available at http://localhost:3000

## API Documentation

Once the server is running, you can access:

- Interactive API documentation: http://localhost:8000/docs
- ReDoc alternative documentation: http://localhost:8000/redoc

### API Endpoints

#### Contract Management
- `GET /api/status` - Check connection status to the blockchain
- `POST /api/contract/deploy` - Deploy a new TransactionChain contract

#### User Management
- `POST /api/users/create` - Create a new user with a username
- `POST /api/users/check` - Check if a user exists by username

#### Balance Management
- `POST /api/balance/add` - Add balance to a user's account
- `POST /api/balance/deposit` - Deposit ETH to a user's account
- `POST /api/balance/check` - Check a user's balance

#### Transaction Management
- `POST /api/transactions/create` - Create a new transaction between users

#### View Data
- `GET /api/transactions/all` - Get all transactions
- `POST /api/transactions/by-id` - Get transaction details by ID
- `POST /api/transactions/by-user` - Get all transactions for a user
- `POST /api/transactions/received` - Get transactions received by a user
- `POST /api/transactions/sent` - Get transactions sent by a user

## Usage Examples

### Create a user

```bash
curl -X POST http://localhost:8000/api/users/create \
  -H "Content-Type: application/json" \
  -d '{"username": "alice"}'
```

### Add balance to a user

```bash
curl -X POST http://localhost:8000/api/balance/add \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "amount": 1000}'
```

### Create a transaction between users

```bash
curl -X POST http://localhost:8000/api/transactions/create \
  -H "Content-Type: application/json" \
  -d '{"sender_username": "alice", "receiver_username": "bob", "amount": 500}'
```

## Web Interface Usage

After starting both frontend and backend servers, navigate to `http://localhost:3000` in your browser. You'll be prompted to log in or create an account to start using Swift Pay.

## CLI Alternative

The project also includes a CLI application for interacting with the blockchain:

```bash
cd layer3
npx hardhat run scripts/transactionManager.ts
```

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Next.js](https://nextjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Hardhat](https://hardhat.org/)
- [shadcn/ui](https://ui.shadcn.com/)
- Dhanush M
- Rahul Bilyar
- Priyanshu Kumar