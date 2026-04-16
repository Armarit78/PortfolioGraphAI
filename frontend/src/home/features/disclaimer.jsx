import { Modal } from "react-bootstrap";
import { Card, Button } from "react-bootstrap";


export function Disclaimer({ isOpen, onClose }) {
    return (
        <Modal show={isOpen} onHide={onClose}>

            <div className="disclaimer">
                <div>
                    <h2>Attention</h2>
                    <p>
                        KyberAI peut commettre des erreurs. Il est recommandé de vérifier les informations importantes.
                        Nous déclinons donc toute responsabilité pour toute erreur ou omission dans le contenu produit par la technologie de l'IA
                    </p>
                    <Button variant="primary" onClick={onClose} className="bg-primary color-white border-0">Fermer</Button>
                </div>

            </div>
        </Modal>
    );
}


