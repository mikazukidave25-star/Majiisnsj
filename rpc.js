import fs from "fs"
import { Client, RichPresence } from "discord.js-selfbot-v13"

// --- SISTEM ANTI CRASH ---
// Mencegah script mati jika ada error jaringan dari Discord
process.on('unhandledRejection', (error) => {
    console.log('[RPC] Peringatan/Error jaringan (Aman diabaikan):', error.message);
});
process.on('uncaughtException', (error) => {
    console.log('[RPC] Error tidak terduga:', error.message);
});

// Baca token dari file
let tokens = [];
try {
    tokens = fs.readFileSync("token.txt", "utf-8")
        .split("\n")
        .map(t => t.trim())
        .filter(t => t.length > 0);
} catch (error) {
    console.log("[RPC] File token.txt tidak ditemukan!");
    process.exit(1);
}

console.log(`[RPC] Total token untuk status: ${tokens.length}`);

tokens.forEach((token, index) => {
    setTimeout(() => {
        const client = new Client({ checkUpdate: false })

        client.on("ready", () => {
            console.log(`[RPC] Status aktif untuk: ${client.user.username}`)

            const rpc = new RichPresence(client)
                .setApplicationId("1205422490969579530")
                .setType("PLAYING")
                .setName("Nyawit 24/7")
                .setDetails("Maul CEO Nyawit")
                .setStartTimestamp(new Date("2026-01-25T00:00:00Z").getTime())
                .setAssetsLargeImage("1312264004382621706") 
                .addButton("YouTube", "https://youtube.com/watch?v=KeCuLeKQC0c")

            client.user.setPresence({
                activities: [rpc]
            })
        })
        
        // Tangkap error per-token agar tidak menular
        client.on("error", (err) => {
            console.log(`[RPC] Token ${index + 1} mengalami error koneksi.`);
        });

        client.login(token).catch(() => {
            console.log(`[RPC] Token ke-${index + 1} invalid / gagal login`)
        })

    }, index * 5000) // delay 5 detik tiap token
})
