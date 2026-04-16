import React, { useEffect, useState } from 'react';
import { Sidebar } from "./features/sideBar";
import { MainContent } from "./features/mainContent";
import { Disclaimer } from "./features/disclaimer";
import "/src/styles/Home.css"
import { useNavigate, useParams } from "react-router-dom";
import { fetchChatHistory } from "./service/api_requests";

const Home = () => {
    const chatId = useParams();
    const navigate = useNavigate();


    const [isDisclaimerOpen, setDisclaimerOpen] = useState(true);
    const [chatList, setChatList] = useState([]);


    useEffect(() => {
        const loadData = async () => {
            const data = await fetchChatHistory();
            if (data) {
                console.log("chatlist : ", data);
                setChatList(data);
            }
        };
        loadData();
    }, [chatId])

    return (
        <div className="home d-flex flex-row">
            {<Disclaimer isOpen={isDisclaimerOpen} onClose={() => { setDisclaimerOpen(false) }} />}
            <Sidebar
                chatList={chatList}
                navigate={navigate}
                setChatList={setChatList}
                chatId={chatId}
            />
            {chatId.chatId ?
                <MainContent
                    chatId={chatId}
                />
                :
                <div className="container-fluid p-0 bg-white rounded-3"></div>
            }


        </div>

    );
};

export default Home;