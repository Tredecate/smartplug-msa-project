/* UPDATE THESE VALUES TO MATCH YOUR SETUP */
const BASE_DOMAIN = window.location.hostname || "localhost"

const REFRESH_RATE_MS = 4000
const PROCESSOR_BASE_URL = `http://${BASE_DOMAIN}:8100`
const ANALYZER_BASE_URL = `http://${BASE_DOMAIN}:8110`

const PROCESSING_STATS_API_URL = PROCESSOR_BASE_URL + "/stats"
const ANALYZER_API_URL = {
    stats: ANALYZER_BASE_URL + "/stats",
    energy: ANALYZER_BASE_URL + "/energy-event?index=-1",
    temperature: ANALYZER_BASE_URL + "/temperature-event?index=-1"
}

let latest_analyzer_stats = {}

// This function fetches and updates the general statistics
const makeReq = (url, cb) => {
    fetch(url)
        .then(res => res.json())
        .then((result) => {
            console.log("Received data: ", result)
            cb(result);
        }).catch((error) => {
            if (error)
            updateErrorMessages(error.message)
        })
}

const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerHTML = objectToHTML(result)

// aight, i'll match your freak. one-liner to convert an object to an HTML list. don't @ me
const objectToHTML = (obj) => Object.entries(obj).map(([key, value]) => `<p><strong>${key}:</strong><br>${value}</p>`).join("")

const getLocaleDateStr = () => (new Date()).toLocaleString()

const getStats = () => {
    document.getElementById("last-updated-value").innerText = getLocaleDateStr()
    
    makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"))
    makeReq(ANALYZER_API_URL.stats, (result) => updateCodeDiv(result, "analyzer-stats") && (latest_analyzer_stats = result) && getEvents())
}

const getEvents = () => {
    latest_analyzer_stats["num_energy_events"] ? makeReq(ANALYZER_API_URL.energy, (result) => updateCodeDiv(result, "event-energy")) : null
    latest_analyzer_stats["num_temperature_events"] ? makeReq(ANALYZER_API_URL.temperature, (result) => updateCodeDiv(result, "event-temperature")) : null
}

const updateErrorMessages = (message) => {
    const id = Date.now()
    console.log("Creation", id)
    msg = document.createElement("div")
    msg.id = `error-${id}`
    msg.innerHTML = `<p>Something happened at ${getLocaleDateStr()}!</p><code>${message}</code>`
    document.getElementById("messages").style.display = "block"
    document.getElementById("messages").prepend(msg)
    setTimeout(() => {
        const elem = document.getElementById(`error-${id}`)
        if (elem) { elem.remove() }
    }, REFRESH_RATE_MS - 1000)
}

const setup = () => {
    getStats()
    setInterval(() => getStats(), REFRESH_RATE_MS) // Update every 4 seconds
}

document.addEventListener('DOMContentLoaded', setup)