import React from "react"

const API_BASE_URL = import.meta.env.VITE_API_URL

//envoie d'un message à l'IA
export const sendMessage = async (messageToSend, setMessages, setIsLoading) => {
    const userMessage = {
        id: Date.now(),
        type: "human",
        content: messageToSend
    };

    setIsLoading(true);
    setMessages((prevMessages) => [...prevMessages, userMessage])

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/ai/request`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    prompt: messageToSend,
                    email: localStorage.getItem("email"),
                    id_chat: localStorage.getItem("id_chat") || null
                })
            });
        const data = await response.json();
        console.log(data)
        setMessages((prevMessages) => [...prevMessages, data.response]);
        setIsLoading(false)

    } catch (error) {
        console.log("erreur lors de la requête API IA : " + error)
    }
}


//charge la liste des chats associés à un compte
export const fetchChatHistory = async () => {
    try {
        console.log("Fetching chat history for email: ", localStorage.getItem("email"));
        const response = await fetch(
            `${API_BASE_URL}/api/ai/getAllChats`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: localStorage.getItem("email")
                })
            }
        );

        const data = await response.json();

        console.log("Data : ", data);

        return data.chats;
    } catch (error) {
        console.log("Erreur lors de la récupération de l'historique des chats : " + error)
    }

}


//charge les messages d'un chat existant
export const changeChat = async (chatId) => {
    localStorage.setItem("id_chat", chatId)
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/ai/getChat`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: localStorage.getItem("email"),
                    id_chat: chatId
                })
            }
        );

        const data = await response.json();
        return data["chat"];

    } catch (error) {
        console.log("Erreur lors de la récupération des messages du chat " + chatId + " : " + error)
    }
}

export const newChat = async () => {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/ai/newChat`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: localStorage.getItem("email")
                })
            }
        );
        const data = await response.json();
        console.log(data.chatId);
        if (data.chatId) {
            return data.chatId;
        }
    } catch (error) {
        console.log("Erreur lors de la création du nouveau chat :  ", error)
    }

}


export const deleteChat = async (chatId) => {
    try {
        const response = await fetch(
            `${API_BASE_URL}/api/ai/deleteChat`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: localStorage.getItem("email"),
                    id_chat: chatId
                })
            }
        );
        const data = await response.json();
        console.log(data.message);
        if (data.message === "Chat deleted successfully") {
            return true;
        }
    } catch (error) {
        console.log("Erreur lors de la suppression du chat :  ", error)
    }

}