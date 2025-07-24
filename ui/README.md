# 🚀 Healthcare and Life Sciences Agent Catalog UI

This is a [Next.js](https://nextjs.org/) project built with **TypeScript** and **React**, bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

---

## 🛠️ Getting Started

### ✅ Prerequisites

Before you begin, make sure you have the following installed:

- [Node.js](https://nodejs.org/) (version 18+ recommended)
- [npm](https://www.npmjs.com/) or your preferred package manager (`yarn`, `pnpm`, `bun`)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html) (configured with appropriate credentials)

---

### 📦 Install Dependencies

```bash
npm install
# or
yarn install
# or
pnpm install
# or
bun install
```

---

### ⚙️ Environment Variables

Create a `.env` file at the root of your project:

```env
AWS_REGION=us-west-2
# Add other environment variables here
```

> ⚠️ Make sure your `.env` file is listed in `.gitignore`.

---

### 💻 Run the Development Server

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Now open [http://localhost:3000](http://localhost:3000) in your browser to view the app.

> Edits to files like `app/page.tsx` will automatically refresh thanks to hot reloading.

---

### 🧪 Recommended Scripts

Run type checking:

```bash
npm run type-check
```

Run ESLint:

```bash
npm run lint
```

---

## 📦 Building for Production

To build and preview the production version locally:

```bash
npm run build
```


## 🔧 Run CloudFormation 

To deploy the Docker-based build pipeline using AWS CloudFormation:

1. Make sure you have the AWS CLI installed and configured.
2. Run the following command to deploy the stack:

```bash
aws cloudformation deploy \
  --template-file cloudformation/docker_build_pipeline.yml \
  --stack-name docker-build-pipeline \
  --capabilities CAPABILITY_IAM
```

> Adjust the `--stack-name` or parameters if required.

To update the stack later, run the same command with updated `yml`.

---

## ⚠️ Security Notice

This deployment will create a **web-accessible application**.  
Ensure you **restrict access to your network** by specifying a proper **CIDR block** in the **Security Group** configuration.

> 📌 Consult your **IT or DevOps team** to configure the correct CIDR range and ensure compliance with your organization's network security policies.

---

## 📚 Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [TypeScript Docs](https://www.typescriptlang.org/docs/)
- [Vercel Platform](https://vercel.com)

---

## 🧑‍💻 Author & License

> Your name or company here  
Licensed under [MIT](LICENSE)

---


