
const API_KEY = "pFTKN_8FQeEkYwX1e86Nhw_dvbz1ya4bLaeHtfDUT0LO"; // Replace with your actual API key
const SCORING_URL = "https://us-south.ml.cloud.ibm.com/ml/v4/deployments/a3c11100-54b6-4a3e-a3de-a73616b6df09/ai_service?version=2021-05-01";

function getToken(errorCallback, loadCallback) {
  const req = new XMLHttpRequest();
  req.addEventListener("load", loadCallback);
  req.addEventListener("error", errorCallback);
  req.open("POST", "https://iam.cloud.ibm.com/identity/token");
  req.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  req.setRequestHeader("Accept", "application/json");
  req.send("grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey=" + API_KEY);
}

function apiPost(token, payload, loadCallback, errorCallback) {
  const oReq = new XMLHttpRequest();
  oReq.addEventListener("load", loadCallback);
  oReq.addEventListener("error", errorCallback);
  oReq.open("POST", SCORING_URL);
  oReq.setRequestHeader("Accept", "application/json");
  oReq.setRequestHeader("Authorization", "Bearer " + token);
  oReq.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
  oReq.send(payload);
}

async function handleSubmit(event) {
  event.preventDefault();
  const userInput = document.getElementById("user-input").value.trim();
  if (!userInput) return;

  // Clear input
  document.getElementById("user-input").value = "";

  // Show user message in chat box
  const userMessage = document.createElement("div");
  userMessage.classList.add("message", "user");
  userMessage.textContent = userInput;
  document.querySelector(".chat-box").appendChild(userMessage);

  getToken(
    (err) => console.error("Failed to get token:", err),
    (req) => {
      let tokenResponse;
      try {
        tokenResponse = JSON.parse(req.responseText);
      } catch (ex) {
        console.error("Error parsing token response:", ex);
        return;
      }

      const payload = JSON.stringify({
        messages: [{ content: userInput, role: "user" }],
      });

      apiPost(
        tokenResponse.access_token,
        payload,
        (oReq) => {
          let parsedPostResponse;
          try {
            parsedPostResponse = JSON.parse(oReq.responseText);
          } catch (ex) {
            console.error("Error parsing API response:", ex);
            return;
          }

          const reply = parsedPostResponse.results?.[0]?.generated_text || "No response";

          const agentMessage = document.createElement("div");
          agentMessage.classList.add("message", "agent");
          const agentTitle = document.createElement("div");
          agentTitle.classList.add("agent-title");
          agentTitle.textContent = "Travel_AI_Agent";
          const messageText = document.createElement("div");
          messageText.classList.add("message-text");
          messageText.textContent = reply;
          agentMessage.appendChild(agentTitle);
          agentMessage.appendChild(messageText);
          document.querySelector(".chat-box").appendChild(agentMessage);
        },
        (error) => console.error("Failed to fetch response:", error)
      );
    }
  );
}


