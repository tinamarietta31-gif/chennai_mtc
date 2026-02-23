// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyC-AofTIfbsDvzzAzzqanAfWhVvEgM2X20",
  authDomain: "chennaimtc-4318a.firebaseapp.com",
  projectId: "chennaimtc-4318a",
  storageBucket: "chennaimtc-4318a.firebasestorage.app",
  messagingSenderId: "968452624468",
  appId: "1:968452624468:web:04490237e71cb08ca49dc1",
  measurementId: "G-HDB8RKB38N"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

export { app, analytics };