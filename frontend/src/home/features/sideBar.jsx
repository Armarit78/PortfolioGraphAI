import { Button } from "react-bootstrap";
import { newChat, deleteChat } from "../service/api_requests";


export const Sidebar = ({ chatList, navigate, setChatList, chatId }) => {
    return (
        <div className="sidebar  d-flex flex-column p-3 w-100">
            <ul className="nav nav-pills flex-column mb-0">
                <li key="new-chat" className="nav-item">
                    <Button onClick={async () => {
                        const res = await newChat();
                        if (res) {
                            setChatList((prev) => [...prev, { id: res, name: "Nouveau chat" }]);
                            navigate(`/chat/${res}`);
                        }

                    }} className="nav-link">Nouveau Chat</Button>
                </li>
            </ul>
            <hr className="border-top border-2 border-white opacity-100 my-0" />
            <ul className="nav nav-pills d-flex flex-row justify-content-start overflow-auto mb-auto custom-scrollbar mt-1">
                {chatList && chatList.map((chat) => (
                    <li key={`chat${chat.id}`} className="nav-item d-flex flex-row w-100 p-0">
                        <Button className={`nav-link justify-content-between align-content-center w-100 text-start text-truncate ${chat.id == chatId.chatId ? "active" : ""}`} style={{ transform: 'translateY(0px)' }} onClick={() => {
                            navigate(`/chat/${chat.id}`)
                        }}>
                            <div>
                                {chat.name}
                            </div>
                        </Button>
                        {chat.id == chatId.chatId && (
                            <Button className="nav-link bg-danger rounded-0 border-0 color-white" style={{ transform: 'translateY(0px)' }} onClick={async () => {
                                const res = await deleteChat(chat.id);
                                if (res) {
                                    setChatList((prev) => prev.filter((c) => c.id !== chat.id));
                                    navigate("/");
                                }
                            }}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" className="bi bi-trash" viewBox="0 0 16 16">
                                    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z" />
                                    <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z" />
                                </svg>
                            </Button>
                        )}

                    </li>
                ))}
            </ul>
            <hr className="border-top border-2 border-white opacity-100 my-0" />
            <ul className="nav nav-pills flex-column mb-0">
                <li key="new-chat" className="nav-item">
                    <Button className="nav-link mt-1">{localStorage.getItem("username") ? localStorage.getItem("username").toUpperCase() : ""}</Button>
                </li>
            </ul>
        </div>
    );
}

export default Sidebar;
