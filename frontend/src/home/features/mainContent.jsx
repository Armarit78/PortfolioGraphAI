
import { Card, InputGroup, Form, Button } from "react-bootstrap";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm"
import remarkBreaks from 'remark-breaks'
import { useEffect, useState } from "react";
import { sendMessage, changeChat } from "../service/api_requests"
import {DataGrid} from "@mui/x-data-grid";
import {Box} from "@mui/material";
import {PortfolioTable} from "../../portfolio/features/portfolioTable";

export const MainContent = ({ chatId }) => {

    const [isLoading, setIsLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [messages, setMessages] = useState([]);
    const [isDeactivate,setIsDeactivate] = useState(false);

    const loadChat = async () => {
        const data = await changeChat(chatId.chatId);
        if (data) {
            console.log("Chat : ", data)
            setMessages(data);
        }
    }

    useEffect(() => {
        if (chatId) {
            loadChat();
        } else {
            setMessages([]);
        }
    }, [chatId]);

    useEffect(()=>{
        messages.map((m,i)=>{
            if(m.payload_type === "portfolio"){
                setIsDeactivate(true);
            }
        })
    },[messages])


    return (
        <div className="container-fluid p-0">
            {/* Zone des messages */}
            <Card className="chat-zone shadow-sm h-100 border-0 rounded-3">
                <Card.Body className="d-flex flex-column-reverse overflow-auto">
                    {isLoading && <div className="spinner-grow primary" role="status" />}
                    {messages.toReversed().map((msg) => {
                        console.log(msg.payload)
                        return (
                        <div className="d-flex flex-column">
                            <div key={msg.id} className={`message ${msg.type} p-2 my-1 rounded-3`}>
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm,remarkBreaks]}
                                    components={{
                                        p: ({ node, ...props }) => <p style={{ margin: 0 }} {...props} />
                                    }}
                                >
                                    {msg.content}
                                </ReactMarkdown>
                            </div>

                            {msg.payload && msg.payload_type === "portfolio" && (
                                    <div className="d-flex justify-content-between">
                                    <PortfolioTable portfolioData={msg.payload.weights}
                                                    columnsToShow={["ticker", "name", "weight"]}/>
                                    </div>
                                )
                            }

                            {msg.response_type === "qcm" && (
                                    <div className="d-flex flex-row justify-content-center mt-2">
                                        {msg.response_options.map((option, index) => (
                                            <div key={index}>
                                                <Button
                                                    key={index}
                                                    className="message ai mx-1 p-2 my-1 rounded-3 border-0"
                                                    onClick={(e) => {
                                                        e.preventDefault();
                                                        if(!isLoading) {
                                                            sendMessage(option, setMessages, setIsLoading);
                                                            setMessage("");
                                                        }
                                                        }}
                                                    style={{minWidth: "150px"}}
                                                >
                                                    {option}
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                            )}

                            {msg.response_type === "affirmation" && (
                                <div className="d-flex flex-row justify-content-center mt-2">
                                    <Button
                                        className="message ai mx-1 p-2 my-1 rounded-3 border-0"
                                        onClick={() => !isLoading === sendMessage("Continuer",setMessages,setIsLoading)}>
                                        Continuer
                                    </Button>
                                </div>
                            )}
                        </div>
                    )})}

                </Card.Body>
                {/* Zone de saisie */}
                <Card.Footer>
                    <Form onSubmit={(e) => {
                        e.preventDefault();
                        if(!isLoading) {

                            sendMessage(message, setMessages, setIsLoading);
                            setMessage("");
                        }
                    }}>
                        <InputGroup>
                            <Form.Control
                                type="text"
                                placeholder="Ecrivez votre message..."
                                value={message}
                                disabled={isDeactivate}
                                onChange={(e) => setMessage(e.target.value)}
                            />
                            <Button variant="primary" type="submit" className="bg-primary border-0">
                                ➤
                            </Button>
                        </InputGroup>
                    </Form>
                    <p className="text-center my-0" style={{ fontSize: "10px" }}>KyberAI est une IA et peut se tromper. Il est recommandé de vérifier les informations.</p>
                </Card.Footer>
            </Card>
        </div>
    );
}
