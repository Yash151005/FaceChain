// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FaceRecord
 * @notice Stores face-identity verification records on-chain for tamper-evident auditing.
 * @dev Each record links a SHA-256 face hash to a matched public URL, timestamped
 *      and attributed to the submitter's wallet address.
 */
contract FaceRecord {

    struct Record {
        string  faceHash;    // SHA-256 hex digest of the 128-dim face encoding
        string  matchedUrl;  // Public URL returned by reverse image search
        uint256 timestamp;   // Block timestamp at time of storage
        address submitter;   // Wallet address that submitted the record
    }

    /// @notice Auto-incrementing record counter (also serves as the next record ID)
    uint256 public recordCount;

    /// @notice Mapping from record ID to its data
    mapping(uint256 => Record) private records;

    /// @notice Emitted every time a new record is stored
    event RecordStored(
        uint256 indexed recordId,
        string  faceHash,
        string  matchedUrl,
        uint256 timestamp,
        address indexed submitter
    );

    /**
     * @notice Store a new face-verification record on-chain.
     * @param _faceHash   SHA-256 hex digest of the face encoding vector
     * @param _matchedUrl Public URL matched via reverse image search
     * @return recordId   The ID assigned to this record
     */
    function storeRecord(
        string memory _faceHash,
        string memory _matchedUrl
    ) external returns (uint256 recordId) {
        recordId = recordCount;

        records[recordId] = Record({
            faceHash:   _faceHash,
            matchedUrl: _matchedUrl,
            timestamp:  block.timestamp,
            submitter:  msg.sender
        });

        emit RecordStored(
            recordId,
            _faceHash,
            _matchedUrl,
            block.timestamp,
            msg.sender
        );

        recordCount++;
    }

    /**
     * @notice Retrieve a previously stored record.
     * @param _recordId The ID of the record to look up
     * @return faceHash   The stored face hash
     * @return matchedUrl The stored matched URL
     * @return timestamp  The block timestamp when the record was created
     * @return submitter  The wallet address that created the record
     */
    function getRecord(uint256 _recordId)
        external
        view
        returns (
            string memory faceHash,
            string memory matchedUrl,
            uint256 timestamp,
            address submitter
        )
    {
        require(_recordId < recordCount, "FaceRecord: record does not exist");
        Record storage r = records[_recordId];
        return (r.faceHash, r.matchedUrl, r.timestamp, r.submitter);
    }
}
