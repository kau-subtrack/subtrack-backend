import axios from 'axios'

const AI_HOST = process.env.AI_HOST || 'http://localhost:5000'

export const sendPickupWebhook = async (parcelId) => {
  try {
    const res = await axios.post(`${AI_HOST}/api/pickup/webhook`, { parcelId })
    console.log(`[AI] /pickup/webhook 호출 성공 - parcelId: ${parcelId}`, res.data)
    return res.data
  } catch (err) {
    console.error(`[AI] /pickup/webhook 호출 실패 - parcelId: ${parcelId}`, err.response?.data || err.message)
    throw err
  }
}