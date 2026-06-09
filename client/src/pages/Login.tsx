import React from 'react';
import { Link } from '@tanstack/react-router';
import { GithubIcon, TwitterIcon } from '../icons';

const ImageLight =
  'https://images.unsplash.com/photo-1497366216548-37526070297c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80';
const ImageDark =
  'https://images.unsplash.com/photo-1497366811353-6870744d04b2?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80';

const Login: React.FC = () => {
  return (
    <div className="flex items-center min-h-screen p-6 bg-gray-50 dark:bg-gray-900">
      <div className="flex-1 h-full max-w-4xl mx-auto overflow-hidden bg-white rounded-lg shadow-xl dark:bg-gray-800">
        <div className="flex flex-col overflow-y-auto md:flex-row">
          <div className="h-32 md:h-auto md:w-1/2">
            <img
              aria-hidden="true"
              className="object-cover w-full h-full dark:hidden"
              src={ImageLight}
              alt="Office"
            />
            <img
              aria-hidden="true"
              className="hidden object-cover w-full h-full dark:block"
              src={ImageDark}
              alt="Office"
            />
          </div>
          <main className="flex items-center justify-center p-6 sm:p-12 md:w-1/2">
            <div className="w-full">
              <h1 className="mb-4 text-xl font-semibold text-gray-700 dark:text-gray-200">Login</h1>
              <label className="block text-sm text-gray-700 dark:text-gray-400">
                <span>Email</span>
                <input
                  className="block w-full mt-1 text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-purple-400 focus:outline-none focus:ring focus:ring-purple-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                  type="email"
                  placeholder="john@doe.com"
                />
              </label>

              <label className="block mt-4 text-sm text-gray-700 dark:text-gray-400">
                <span>Password</span>
                <input
                  className="block w-full mt-1 text-sm border border-gray-300 rounded-md px-3 py-2 focus:border-purple-400 focus:outline-none focus:ring focus:ring-purple-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300"
                  type="password"
                  placeholder="***************"
                />
              </label>

              <Link
                to="/"
                className="block w-full mt-4 px-5 py-2 text-sm font-medium leading-5 text-center text-white transition-colors duration-150 bg-purple-600 border border-transparent rounded-lg hover:bg-purple-700 focus:outline-none focus:shadow-outline-purple"
              >
                Log in
              </Link>

              <hr className="my-8" />

              <button
                type="button"
                className="inline-flex items-center justify-center w-full px-5 py-2 text-sm font-medium leading-5 text-gray-700 transition-colors duration-150 bg-white border border-gray-300 rounded-lg dark:text-gray-200 dark:bg-gray-700 dark:border-gray-600 hover:border-gray-500 focus:border-gray-500 focus:outline-none focus:shadow-outline-gray"
              >
                <GithubIcon className="w-4 h-4 mr-2" aria-hidden="true" />
                Github
              </button>
              <button
                type="button"
                className="inline-flex items-center justify-center w-full mt-4 px-5 py-2 text-sm font-medium leading-5 text-gray-700 transition-colors duration-150 bg-white border border-gray-300 rounded-lg dark:text-gray-200 dark:bg-gray-700 dark:border-gray-600 hover:border-gray-500 focus:border-gray-500 focus:outline-none focus:shadow-outline-gray"
              >
                <TwitterIcon className="w-4 h-4 mr-2" aria-hidden="true" />
                Twitter
              </button>

              <p className="mt-4">
                <Link
                  className="text-sm font-medium text-purple-600 dark:text-purple-400 hover:underline"
                  to="/"
                >
                  Forgot your password?
                </Link>
              </p>
              <p className="mt-1">
                <Link
                  className="text-sm font-medium text-purple-600 dark:text-purple-400 hover:underline"
                  to="/"
                >
                  Create account
                </Link>
              </p>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default Login;
