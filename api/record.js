import { Contract, JsonRpcProvider, Wallet } from "ethers";

const ABI = [
  "function storeRecord(string _faceHash, string _matchedUrl) returns (uint256 recordId)",
  "event RecordStored(uint256 indexed recordId, string faceHash, string matchedUrl, uint256 timestamp, address indexed submitter)",
];

function requireHexHash(value) {
  if (typeof value !== "string" || !/^[a-f0-9]{64}$/i.test(value)) {
    throw new Error("The biometric fingerprint is invalid.");
  }
  return value.toLowerCase();
}

function requirePublicUrl(value) {
  const url = new URL(value);
  if (url.protocol !== "https:" && url.protocol !== "http:") throw new Error("The matched URL is invalid.");
  return url.toString();
}

export default async function handler(request, response) {
  if (request.method !== "POST") {
    response.setHeader("Allow", "POST");
    return response.status(405).json({ error: "Method not allowed." });
  }

  const { ALCHEMY_RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS } = process.env;
  if (!ALCHEMY_RPC_URL || !PRIVATE_KEY || !CONTRACT_ADDRESS) {
    return response.status(503).json({ error: "Blockchain recording is not configured." });
  }

  try {
    const faceHash = requireHexHash(request.body?.faceHash);
    const matchedUrl = requirePublicUrl(request.body?.matchedUrl);
    const provider = new JsonRpcProvider(ALCHEMY_RPC_URL, 80002, { staticNetwork: true });
    const wallet = new Wallet(PRIVATE_KEY.startsWith("0x") ? PRIVATE_KEY : `0x${PRIVATE_KEY}`, provider);
    const contract = new Contract(CONTRACT_ADDRESS, ABI, wallet);
    const transaction = await contract.storeRecord(faceHash, matchedUrl, {
      gasLimit: 500000,
      maxFeePerGas: 50000000000n,
      maxPriorityFeePerGas: 30000000000n,
    });
    const receipt = await transaction.wait();
    if (!receipt || receipt.status !== 1) throw new Error("The transaction was reverted.");

    let recordId = null;
    for (const log of receipt.logs) {
      try {
        const parsed = contract.interface.parseLog(log);
        if (parsed?.name === "RecordStored") recordId = parsed.args.recordId.toString();
      } catch {
        // Ignore logs from other contracts.
      }
    }

    return response.status(200).json({
      txHash: transaction.hash,
      blockNumber: receipt.blockNumber,
      gasUsed: receipt.gasUsed.toString(),
      recordId,
      wallet: wallet.address,
      explorerUrl: `https://amoy.polygonscan.com/tx/${transaction.hash}`,
    });
  } catch (error) {
    return response.status(400).json({ error: error.shortMessage || error.message || "Blockchain transaction failed." });
  }
}
