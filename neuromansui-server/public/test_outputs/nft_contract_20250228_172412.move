module 0x0::my_module {

    // Import the UID type for Sui objects.
    use sui::object::UID;
    // Import the transaction context which provides the sender and fresh id functionality.
    use sui::tx_context::TxContext;

    ////////////////////////////////////////////////////////////////////////////
    // Helper: Wrapped UID with drop ability
    ////////////////////////////////////////////////////////////////////////////

    // The Sui framework’s UID type does not have the drop ability, which is required
    // for resources that are returned by entry functions. To work around this, we wrap
    // UID in a new type (MyUID) that provides the drop ability.
    public struct MyUID has key, store, drop {
        inner: UID
    }

    // Generates a new MyUID using the transaction context.
    public fun new_myuid(ctx: &mut TxContext): MyUID {
        // TxContext::fresh_id(ctx) returns a fresh UID.
        MyUID { inner: TxContext::fresh_id(ctx) }
    }

    ////////////////////////////////////////////////////////////////////////////
    // Resource Declarations
    ////////////////////////////////////////////////////////////////////////////

    // NFT resource representing a non-fungible token with metadata.
    // Sui objects must have an id as the first field; here we use MyUID.
    public struct NFT has key, store, drop {
        id: MyUID,              // Unique object identifier (wrapped UID).
        owner: address,         // Owner's address.
        name: vector<u8>,       // NFT name.
        description: vector<u8>,// NFT description.
        image_url: vector<u8>   // URL to the NFT image.
    }

    // MintCap resource grants minting authority.
    // It is a Sui object and must have an id field as its first field.
    public struct MintCap has key, store, drop {
        id: MyUID,       // Unique identifier for the minting capability.
        admin: address   // Administrator authorized to mint NFTs.
    }

    ////////////////////////////////////////////////////////////////////////////
    // MintCap Creation Function
    ////////////////////////////////////////////////////////////////////////////

    // Creates a minting capability. The sender of the transaction becomes the admin.
    public entry fun create_mint_cap(ctx: &mut TxContext): MintCap {
        let admin_addr = ctx.sender();
        let cap_id = new_myuid(ctx);
        MintCap { id: cap_id, admin: admin_addr }
    }

    ////////////////////////////////////////////////////////////////////////////
    // NFT Minting Function
    ////////////////////////////////////////////////////////////////////////////

    // Mints a new NFT with provided metadata.
    // Only the admin from the MintCap is allowed to mint an NFT.
    public entry fun mint_nft(
        mint_cap: MintCap,
        recipient: address,
        name: vector<u8>,
        description: vector<u8>,
        image_url: vector<u8>,
        ctx: &mut TxContext
    ): (NFT, MintCap) {
        let sender = ctx.sender();
        // Access control: only the admin can mint an NFT.
        assert!(sender == mint_cap.admin, 100);
        let new_id = new_myuid(ctx);
        let nft = NFT {
            id: new_id,
            owner: recipient,
            name,
            description,
            image_url
        };
        // Return both the minted NFT and the unchanged minting capability.
        (nft, mint_cap)
    }

    ////////////////////////////////////////////////////////////////////////////
    // NFT Transfer Function
    ////////////////////////////////////////////////////////////////////////////

    // Transfers an NFT to a new owner.
    // Only the current owner (determined by tx context) may initiate the transfer.
    public entry fun transfer_nft(
        nft: NFT,
        new_owner: address,
        ctx: &mut TxContext
    ): NFT {
        let sender = ctx.sender();
        // Destructure the NFT to retrieve its fields.
        let NFT { id, owner, name, description, image_url } = nft;
        // Verify that only the owner can transfer the NFT.
        assert!(sender == owner, 101);
        NFT {
            id,
            owner: new_owner,
            name,
            description,
            image_url
        }
    }

    ////////////////////////////////////////////////////////////////////////////
    // NFT Metadata Update Function
    ////////////////////////////////////////////////////////////////////////////

    // Updates the metadata for an NFT.
    // Only the owner (determined by tx context) is allowed to update metadata.
    public entry fun update_nft_metadata(
        nft: NFT,
        new_name: vector<u8>,
        new_description: vector<u8>,
        new_image_url: vector<u8>,
        ctx: &mut TxContext
    ): NFT {
        let sender = ctx.sender();
        // Destructure the NFT to extract its id and owner.
        let NFT { id, owner, name: _, description: _, image_url: _ } = nft;
        // Verify that the sender is the current owner.
        assert!(sender == owner, 102);
        NFT {
            id,
            owner,
            name: new_name,
            description: new_description,
            image_url: new_image_url
        }
    }
}