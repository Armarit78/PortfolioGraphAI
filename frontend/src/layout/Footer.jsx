import React from 'react';
import "../styles/Footer.css"


const Footer = () => {
    return (
        <footer className="py-2 mb-0">
            <div className="row">
                <div className="col-12 d-flex justify-content-center">
                    <p>&copy; 2026 KyberAI</p>
                </div>
                <div className="col-6 col-md d-flex flex-column align-items-center">
                    <p>Dévelopé par : </p>
                    <p>Benyahia Mathis <br /> Fortuny Arnaud <br /> Poret Guillaume</p>
                </div>
                <div className="col-6 col-md d-flex flex-column align-items-center">
                    <p>En partenariat avec :</p>
                    <p>Accenture <br /> CentraleSupélec</p>
                </div>
            </div>
        </footer>
    );
};

export default Footer;